"""
Event Booking Configuration Models

EventBookingDate   — 活動可選日期（每個活動可設定多個搭車日期）
EventPickupLocation — 上車地點（每個活動可設定多個地點）
EventPriceRule     — 依日期 + 地點組合的價格設定
EventFormConfig    — 表單欄位是否顯示 / 必填

所有 Model 刪除時使用軟刪除或外鍵 SET NULL，不影響已存在的 Order 資料。
"""
from datetime import datetime
from app import db


class EventBookingDate(db.Model):
    __tablename__ = "event_booking_dates"

    id           = db.Column(db.Integer, primary_key=True)
    event_page_id = db.Column(
        db.Integer,
        db.ForeignKey("event_pages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date_value   = db.Column(db.String(30), nullable=False)   # e.g. "2025-11-22"
    label        = db.Column(db.String(100), nullable=True)   # e.g. "11/22（日）第一場"
    sort_order   = db.Column(db.Integer, nullable=False, default=0)
    is_active    = db.Column(db.Boolean, nullable=False, default=True)
    capacity     = db.Column(db.Integer, nullable=True)        # 該日期座位上限，NULL = 無限制
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    event_page = db.relationship("EventPage", backref=db.backref(
        "booking_dates", lazy="dynamic", order_by="EventBookingDate.sort_order"
    ))


class EventPickupLocation(db.Model):
    __tablename__ = "event_pickup_locations"

    id           = db.Column(db.Integer, primary_key=True)
    event_page_id = db.Column(
        db.Integer,
        db.ForeignKey("event_pages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name         = db.Column(db.String(100), nullable=False)   # 顯示名稱，e.g. "台北車站"
    address      = db.Column(db.String(300), nullable=True)    # 地址或備註
    map_url      = db.Column(db.String(500), nullable=True)    # Google Maps 連結
    sort_order   = db.Column(db.Integer, nullable=False, default=0)
    is_active    = db.Column(db.Boolean, nullable=False, default=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    event_page = db.relationship("EventPage", backref=db.backref(
        "pickup_locations", lazy="dynamic", order_by="EventPickupLocation.sort_order"
    ))


class EventPriceRule(db.Model):
    """
    依日期 + 地點組合設定價格。
    date_value 或 location_id 為 NULL 表示「適用所有日期/地點」（預設規則）。
    查詢優先順序：日期+地點 > 日期 > 地點 > 全局預設（EventPage.price）。
    """
    __tablename__ = "event_price_rules"

    id              = db.Column(db.Integer, primary_key=True)
    event_page_id   = db.Column(
        db.Integer,
        db.ForeignKey("event_pages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    booking_date_id = db.Column(
        db.Integer,
        db.ForeignKey("event_booking_dates.id", ondelete="CASCADE"),
        nullable=True,
    )
    location_id     = db.Column(
        db.Integer,
        db.ForeignKey("event_pickup_locations.id", ondelete="CASCADE"),
        nullable=True,
    )
    price           = db.Column(db.Integer, nullable=False)
    deposit         = db.Column(db.Integer, nullable=False, default=0)
    label           = db.Column(db.String(100), nullable=True)   # 後台顯示名稱
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    event_page    = db.relationship("EventPage", backref=db.backref("price_rules", lazy="dynamic"))
    booking_date  = db.relationship("EventBookingDate", backref=db.backref("price_rules", lazy="dynamic"))
    location      = db.relationship("EventPickupLocation", backref=db.backref("price_rules", lazy="dynamic"))


class EventFormConfig(db.Model):
    """
    控制 booking.html 表單欄位的顯示 / 必填狀態。
    每個欄位一列；若無紀錄，表示使用預設值（顯示且按原本必填設定）。
    """
    __tablename__ = "event_form_configs"

    id              = db.Column(db.Integer, primary_key=True)
    event_page_id   = db.Column(
        db.Integer,
        db.ForeignKey("event_pages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    field_name      = db.Column(db.String(50), nullable=False)   # e.g. "emergency_phone", "companion_names", "remark"
    is_visible      = db.Column(db.Boolean, nullable=False, default=True)
    is_required     = db.Column(db.Boolean, nullable=False, default=False)
    label_override  = db.Column(db.String(100), nullable=True)   # 自訂欄位標題
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    event_page = db.relationship("EventPage", backref=db.backref("form_configs", lazy="dynamic"))

    __table_args__ = (
        db.UniqueConstraint("event_page_id", "field_name", name="uq_event_form_field"),
    )
