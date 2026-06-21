"""
OrderEvent — 訂單與活動頁的 Mapping 記錄。

規則：
- BTS 舊訂單：不建立任何 mapping，完全不受影響
- 新活動訂單：建立 mapping，可透過 order.event_mappings 存取
- unique(order_id, event_page_id) 避免重複
"""
from datetime import datetime
from app import db


class OrderEvent(db.Model):
    __tablename__ = "order_events"

    id            = db.Column(db.Integer, primary_key=True)
    order_id      = db.Column(db.Integer, db.ForeignKey("orders.id",      ondelete="CASCADE"), nullable=False, index=True)
    event_page_id = db.Column(db.Integer, db.ForeignKey("event_pages.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("order_id", "event_page_id", name="uq_order_event"),
    )

    order      = db.relationship("Order",     foreign_keys=[order_id],
                                 backref=db.backref("event_mappings", lazy="dynamic", cascade="all, delete-orphan"))
    event_page = db.relationship("EventPage", foreign_keys=[event_page_id],
                                 backref=db.backref("order_mappings", lazy="dynamic"))
