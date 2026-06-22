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
    vehicle_id: int | None = None,
) -> DispatchEvent:
    de = DispatchEvent(
        event_page_id  = event_page_id or None,
        dispatch_date  = dispatch_date,
        departure_city = departure_city,
        notes          = notes,
        vehicle_id     = vehicle_id or None,
        created_at     = datetime.utcnow(),
        updated_at     = datetime.utcnow(),
    )
    db.session.add(de)
    db.session.flush()
    return de


def delete_dispatch_event(dispatch_event_id: int) -> None:
    """刪除車次，訂單自動回到待排狀態（因 CASCADE DELETE 移除 event_orders）。"""
    de = DispatchEvent.query.get_or_404(dispatch_event_id)
    db.session.delete(de)


def move_order_between_events(order_id: int, target_event_id: int | None) -> tuple[bool, str]:
    """
    移動訂單到另一台車（target_event_id=None 表示移回待排）。
    不檢查人數上限（由呼叫方決定是否要檢查）。
    """
    order = Order.query.get(order_id)
    if not order:
        return False, "訂單不存在"

    # 先從目前所在的 DispatchEvent 移除
    existing = (
        DispatchEventOrder.query
        .filter_by(order_id=order_id)
        .first()
    )
    if existing:
        old_de = existing.dispatch_event
        db.session.delete(existing)
        db.session.flush()
        if old_de:
            old_de.recalc()

    if target_event_id is None:
        return True, "已移回待排"

    target = DispatchEvent.query.get(target_event_id)
    if not target:
        return False, "目標車次不存在"

    deo = DispatchEventOrder(dispatch_event_id=target_event_id, order_id=order_id)
    db.session.add(deo)
    db.session.flush()
    target.recalc()
    target.updated_at = datetime.utcnow()
    return True, "OK"


def get_departure_dates_for_event(event_page_id: int | None) -> list[str]:
    """取得該活動有付款訂單的出發日期清單（去重排序）。"""
    q = Order.query.filter(
        Order.payment_status.in_(["訂金已確認", "已完成"])
    )
    if event_page_id == 0:
        q = q.filter(Order.event_page_id.is_(None))
    elif event_page_id:
        q = q.filter(Order.event_page_id == event_page_id)
    rows = q.with_entities(Order.departure_date).distinct().all()
    dates = sorted({r[0] for r in rows if r[0]})
    return dates


def get_kanban_data(event_page_id: int | None, dispatch_date: str) -> dict:
    """
    回傳看板所需資料：
    - unassigned: 尚未分配的訂單
    - dispatch_items: [{de, orders, current, max, full}]
    """
    # 已分配到這個日期的 DispatchEvent
    q = DispatchEvent.query.filter_by(dispatch_date=dispatch_date)
    if event_page_id == 0:
        q = q.filter(DispatchEvent.event_page_id.is_(None))
    elif event_page_id is not None:
        q = q.filter(DispatchEvent.event_page_id == event_page_id)
    dispatch_events = q.order_by(DispatchEvent.created_at.asc()).all()

    # 已分配的 order_ids
    assigned_ids = {
        deo.order_id
        for de in dispatch_events
        for deo in de.event_orders
    }

    # 未分配訂單（限定日期）
    uq = Order.query.filter(
        Order.payment_status.in_(["訂金已確認", "已完成"]),
        Order.departure_date == dispatch_date,
    )
    if event_page_id == 0:
        uq = uq.filter(Order.event_page_id.is_(None))
    elif event_page_id is not None:
        uq = uq.filter(Order.event_page_id == event_page_id)
    unassigned = [o for o in uq.order_by(Order.created_at.asc()).all()
                  if o.id not in assigned_ids]

    dispatch_items = []
    for de in dispatch_events:
        orders = [eo.order for eo in de.event_orders if eo.order]
        current = sum(o.passenger_count for o in orders)
        mx = de.seat_limit
        dispatch_items.append({
            "de":      de,
            "orders":  orders,
            "current": current,
            "max":     mx,
            "full":    current >= mx,
        })

    return {"unassigned": unassigned, "dispatch_items": dispatch_items}


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
