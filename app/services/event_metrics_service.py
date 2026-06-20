"""
event_metrics_service.py

負責計算並持久化 EventMetrics 統計快照。
所有統計邏輯集中在此；Route 只呼叫此模組的公開函式。

公開 API：
    refresh_metrics(event_page_id)   → EventMetrics
    increment_page_views(event_page_id) → None
    backfill_event_metrics()         → int  (更新筆數)
"""
from datetime import datetime
from decimal import Decimal

from app import db
from app.models.event_metrics import EventMetrics
from app.models.order import Order


# 視為「已付款」的 payment_status 值
_PAID_STATUSES = ("訂金已確認", "已完成")
# 視為「已取消」的 payment_status 值
_CANCELLED_STATUSES = ("已取消",)
# 視為「未付款」的 payment_status 值（待確認也算未付）
_UNPAID_STATUSES = ("待付款", "待確認")


def refresh_metrics(event_page_id: int) -> EventMetrics:
    """
    重新計算指定活動頁的統計數據並寫入 event_metrics。
    若該活動尚無統計列則建立；若已有則更新（保留 page_views）。
    呼叫端需自行 commit（或依賴外層 transaction）。
    """
    # 查詢該活動所有訂單
    orders = Order.query.filter_by(event_page_id=event_page_id).all()

    booking_count   = len(orders)
    paid_orders     = [o for o in orders if o.payment_status in _PAID_STATUSES]
    unpaid_orders   = [o for o in orders if o.payment_status in _UNPAID_STATUSES]
    cancelled_orders = [o for o in orders if o.payment_status in _CANCELLED_STATUSES]

    paid_count      = len(paid_orders)
    unpaid_count    = len(unpaid_orders)
    cancelled_count = len(cancelled_orders)
    passenger_count = sum(o.passenger_count for o in orders)
    deposit_amount  = sum(o.deposit_amount  for o in paid_orders)
    revenue_amount  = sum(o.total_amount    for o in [o for o in orders if o.payment_status == "已完成"])
    completion_rate = (
        Decimal(str(round(paid_count / booking_count * 100, 2)))
        if booking_count > 0 else Decimal("0")
    )

    m = EventMetrics.query.filter_by(event_page_id=event_page_id).first()
    if m is None:
        m = EventMetrics(event_page_id=event_page_id, created_at=datetime.utcnow())
        db.session.add(m)

    m.booking_count   = booking_count
    m.paid_count      = paid_count
    m.unpaid_count    = unpaid_count
    m.cancelled_count = cancelled_count
    m.passenger_count = passenger_count
    m.deposit_amount  = deposit_amount
    m.revenue_amount  = revenue_amount
    m.completion_rate = completion_rate
    m.updated_at      = datetime.utcnow()

    return m


def increment_page_views(event_page_id: int) -> None:
    """
    將指定活動的 page_views +1。
    若統計列不存在則先建立（page_views=1，其他欄位為 0）。
    使用獨立 try/except 避免計數失敗影響主流程。
    """
    try:
        m = EventMetrics.query.filter_by(event_page_id=event_page_id).first()
        if m is None:
            m = EventMetrics(
                event_page_id=event_page_id,
                page_views=1,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.session.add(m)
        else:
            m.page_views = (m.page_views or 0) + 1
            m.updated_at = datetime.utcnow()
        db.session.commit()
    except Exception:
        db.session.rollback()


def backfill_event_metrics() -> int:
    """
    重新計算所有未刪除活動的統計數據。
    回傳更新筆數。
    """
    from app.models.event_page import EventPage
    event_pages = EventPage.query.filter(EventPage.deleted_at.is_(None)).all()
    count = 0
    for ep in event_pages:
        try:
            refresh_metrics(ep.id)
            db.session.commit()
            count += 1
        except Exception:
            db.session.rollback()
    return count
