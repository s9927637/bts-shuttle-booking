from datetime import datetime
from app import db

class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    order_no = db.Column(db.String(30), unique=True, nullable=False)
    contact_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    emergency_phone = db.Column(db.String(20))
    departure_date = db.Column(db.String(20), nullable=False)
    passenger_count = db.Column(db.Integer, nullable=False)
    companion_names = db.Column(db.Text)
    remark = db.Column(db.Text)
    total_amount    = db.Column(db.Integer, nullable=False)
    deposit_amount  = db.Column(db.Integer, nullable=False, default=0)
    balance_amount  = db.Column(db.Integer, nullable=False, default=0)
    payment_status  = db.Column(db.String(20), default="待付款")
    vehicle_id   = db.Column(db.Integer, db.ForeignKey("vehicles.id"))
    dispatch_id  = db.Column(db.Integer, db.ForeignKey("dispatches.id"), nullable=True)
    vehicle_type = db.Column(db.String(20), nullable=False, default="minibus")
    group_id     = db.Column(db.String(30), nullable=True, index=True)
    coupon_code       = db.Column(db.String(30), nullable=True)
    discount_amount   = db.Column(db.Integer, nullable=False, default=0)
    line_user_id      = db.Column(db.String(50), nullable=True, index=True)
    display_name      = db.Column(db.String(100), nullable=True)
    terms_accepted_at = db.Column(db.DateTime, nullable=True)
    terms_version     = db.Column(db.String(10), nullable=True)
    created_at        = db.Column(db.DateTime, default=datetime.utcnow)

    # 活動專屬欄位（NULL = 原 BTS 訂單，向前相容）
    pickup_location     = db.Column(db.String(100), nullable=True)   # 上車地點名稱（快照，不存 FK）

    # 活動頁串接（NULL = 原 BTS 訂單，不影響既有資料）
    event_page_id = db.Column(
        db.Integer,
        db.ForeignKey("event_pages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_page = db.relationship(
        "EventPage",
        foreign_keys=[event_page_id],
        backref=db.backref("orders", lazy="dynamic"),
    )
