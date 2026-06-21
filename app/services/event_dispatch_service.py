"""
event_dispatch_service — 多活動排車業務邏輯。

原則：
- 純讀寫 dispatch_events / dispatch_event_orders，不碰 dispatches / orders 結構
- BTS 舊排車資料完全隔離
"""
from __future__ import annotations
from datetime import datetime, date
from app import db
from app.models.dispatch_event import DispatchEvent, DispatchEventOrder
from app.models.order import Order
from app.models.event_page import EventPage


# ── 查詢 ──────────────────────────────────────────────────────────────────────

def get_all_dispatch_events(event_page_id: int | None = None) -> list[DispatchEvent]:
    q = DispatchEvent.query
    if event_page_id == 0:
        q = q.filter(DispatchEvent.event_page_id.is_(None))
    elif event_page_id:
        q = q.filter(DispatchEvent.event_page_id == event_page_id)
    return q.order_by(DispatchEvent.dispatch_date.desc(), DispatchEvent.created_at.desc()).all()


def get_dispatch_event_detail(dispatch_event_id: int) -> dict:
    de = DispatchEvent.query.get_or_404(dispatch_event_id)
    orders = [eo.order for eo in de.event_orders if eo.order]
    paid   = [o for o in orders if o.payment_status in ("訂金已確認", "已完成")]
    unpaid = [o for o in orders if o.payment_status not in ("訂金已確認", "已完成")]
    return {
        "dispatch_event": de,
        "orders":         orders,
        "paid_orders":    paid,
        "unpaid_orders":  unpaid,
        "total_pax":      sum(o.passenger_count for o in orders),
        "paid_pax":       sum(o.passenger_count for o in paid),
        "unpaid_pax":     sum(o.passenger_count for o in unpaid),
    }


def get_unassigned_orders(event_page_id: int | None) -> list[Order]:
    """取得尚未加入任何 DispatchEvent 的訂單（已付款）。"""
    assigned_ids = db.session.query(DispatchEventOrder.order_id).scalar_subquery()
    q = (
        Order.query
        .filter(Order.payment_status.in_(["訂金已確認", "已完成"]))
        .filter(~Order.id.in_(assigned_ids))
    )
    if event_page_id == 0:
        q = q.filter(Order.event_page_id.is_(None))
    elif event_page_id:
        q = q.filter(Order.event_page_id == event_page_id)
    return q.order_by(Order.created_at.asc()).all()


# ── Dashboard 統計 ─────────────────────────────────────────────────────────────

def get_today_dispatch_events() -> list[DispatchEvent]:
    today_str = date.today().strftime("%-m/%-d")  # 配合現有格式，如 6/21
    # 若 dispatch_date 格式多樣，以 contains 模糊比對
    return (
        DispatchEvent.query
        .filter(DispatchEvent.status.in_(["已確認", "已出發"]))
        .order_by(DispatchEvent.dispatch_date)
        .all()
    )


def get_pending_dispatch_events() -> list[DispatchEvent]:
    return (
        DispatchEvent.query
        .filter(DispatchEvent.status.in_(["規劃中", "確認中"]))
        .order_by(DispatchEvent.dispatch_date)
        .limit(10)
        .all()
    )


def get_dispatch_summary() -> dict:
    from sqlalchemy import func
    total_events    = DispatchEvent.query.count()
    pending_events  = DispatchEvent.query.filter(
        DispatchEvent.status.in_(["規劃中", "確認中"])
    ).count()
    active_events   = DispatchEvent.query.filter(
        DispatchEvent.status.in_(["已確認", "已出發"])
    ).count()
    total_pax       = db.session.query(
        func.sum(DispatchEvent.passenger_count)
    ).scalar() or 0
    return {
        "total_events":   total_events,
        "pending_events": pending_events,
        "active_events":  active_events,
        "total_pax":      int(total_pax),
    }


# ── 建立 / 修改 ───────────────────────────────────────────────────────────────

def create_dispatch_event(
    dispatch_date: str,
    event_page_id: int | None,
    departure_city: str | None = None,
    notes: str | None = None,
) -> DispatchEvent:
    de = DispatchEvent(
        event_page_id  = event_page_id or None,
        dispatch_date  = dispatch_date,
        departure_city = departure_city,
        notes          = notes,
        created_at     = datetime.utcnow(),
        updated_at     = datetime.utcnow(),
    )
    db.session.add(de)
    db.session.flush()
    return de


def add_order_to_dispatch_event(dispatch_event_id: int, order_id: int) -> tuple[bool, str]:
    de    = DispatchEvent.query.get(dispatch_event_id)
    order = Order.query.get(order_id)
    if not de:
        return False, "DispatchEvent 不存在"
    if not order:
        return False, "訂單不存在"
    existing = DispatchEventOrder.query.filter_by(
        dispatch_event_id=dispatch_event_id, order_id=order_id
    ).first()
    if existing:
        return False, "訂單已在此車次"
    deo = DispatchEventOrder(dispatch_event_id=dispatch_event_id, order_id=order_id)
    db.session.add(deo)
    de.recalc()
    de.updated_at = datetime.utcnow()
    return True, "OK"


def remove_order_from_dispatch_event(dispatch_event_id: int, order_id: int) -> tuple[bool, str]:
    deo = DispatchEventOrder.query.filter_by(
        dispatch_event_id=dispatch_event_id, order_id=order_id
    ).first()
    if not deo:
        return False, "關聯不存在"
    de = deo.dispatch_event
    db.session.delete(deo)
    db.session.flush()
    de.recalc()
    de.updated_at = datetime.utcnow()
    return True, "OK"
