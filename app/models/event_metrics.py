from datetime import datetime
from decimal import Decimal
from app import db


class EventMetrics(db.Model):
    __tablename__ = "event_metrics"

    id             = db.Column(db.Integer, primary_key=True)
    event_page_id  = db.Column(
        db.Integer,
        db.ForeignKey("event_pages.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    page_views      = db.Column(db.Integer, nullable=False, default=0)
    booking_count   = db.Column(db.Integer, nullable=False, default=0)
    paid_count      = db.Column(db.Integer, nullable=False, default=0)
    unpaid_count    = db.Column(db.Integer, nullable=False, default=0)
    cancelled_count = db.Column(db.Integer, nullable=False, default=0)
    passenger_count = db.Column(db.Integer, nullable=False, default=0)
    deposit_amount  = db.Column(db.Integer, nullable=False, default=0)
    revenue_amount  = db.Column(db.Integer, nullable=False, default=0)
    completion_rate = db.Column(db.Numeric(5, 2), nullable=False, default=Decimal("0"))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    event_page = db.relationship(
        "EventPage",
        foreign_keys=[event_page_id],
        backref=db.backref("metrics", uselist=False),
    )

    @property
    def conversion_rate(self) -> float:
        """付款轉換率 = paid_count / booking_count * 100"""
        if not self.booking_count:
            return 0.0
        return round(self.paid_count / self.booking_count * 100, 1)

    @property
    def avg_order_value(self) -> int:
        """平均客單價 = revenue_amount / paid_count"""
        if not self.paid_count:
            return 0
        return int(self.revenue_amount / self.paid_count)
