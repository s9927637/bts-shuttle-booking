"""
DispatchEvent / DispatchEventOrder — 多活動排車 Mapping。

規則：
- 不修改既有 dispatches / dispatch_orders / orders 結構
- BTS 舊排車資料完全不受影響
- event_page_id=NULL → BTS 活動車次
"""
from datetime import datetime
from app import db

_STATUS_META = {
    "規劃中": ("規劃中", "gray"),
    "確認中": ("確認中", "yellow"),
    "已確認": ("已確認", "green"),
    "已出發": ("已出發", "blue"),
    "已完成": ("已完成", "gray"),
    "已取消": ("已取消", "red"),
}


class DispatchEvent(db.Model):
    __tablename__ = "dispatch_events"

    id              = db.Column(db.Integer, primary_key=True)
    event_page_id   = db.Column(db.Integer,
                                db.ForeignKey("event_pages.id", ondelete="SET NULL"),
                                nullable=True, index=True)
    dispatch_date   = db.Column(db.String(50),  nullable=False, index=True)
    departure_city  = db.Column(db.String(100), nullable=True)
    vehicle_count   = db.Column(db.Integer,     nullable=False, default=0)
    passenger_count = db.Column(db.Integer,     nullable=False, default=0)
    status          = db.Column(db.String(20),  nullable=False, default="規劃中", index=True)
    notes           = db.Column(db.Text,        nullable=True)
    created_at      = db.Column(db.DateTime,    default=datetime.utcnow)
    updated_at      = db.Column(db.DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)

    event_page    = db.relationship("EventPage", foreign_keys=[event_page_id],
                                    backref=db.backref("dispatch_events", lazy="dynamic"))
    event_orders  = db.relationship("DispatchEventOrder", backref="dispatch_event",
                                    lazy="dynamic", cascade="all, delete-orphan")

    @property
    def status_label(self) -> str:
        return _STATUS_META.get(self.status, ("—", "gray"))[0]

    @property
    def status_color(self) -> str:
        return _STATUS_META.get(self.status, ("—", "gray"))[1]

    @property
    def event_title(self) -> str:
        return self.event_page.title if self.event_page else "BTS 高雄演唱會"

    @property
    def artist_name(self) -> str:
        return self.event_page.artist_name if self.event_page else "BTS"

    def recalc(self):
        """根據目前 event_orders 重算 passenger_count。"""
        total = sum(
            (eo.order.passenger_count or 0)
            for eo in self.event_orders
            if eo.order
        )
        self.passenger_count = total


class DispatchEventOrder(db.Model):
    __tablename__ = "dispatch_event_orders"

    id                = db.Column(db.Integer, primary_key=True)
    dispatch_event_id = db.Column(db.Integer,
                                  db.ForeignKey("dispatch_events.id", ondelete="CASCADE"),
                                  nullable=False, index=True)
    order_id          = db.Column(db.Integer,
                                  db.ForeignKey("orders.id", ondelete="CASCADE"),
                                  nullable=False, index=True)
    created_at        = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("dispatch_event_id", "order_id", name="uq_dispatch_event_order"),
    )

    order = db.relationship("Order", foreign_keys=[order_id],
                            backref=db.backref("dispatch_event_orders", lazy="dynamic"))
