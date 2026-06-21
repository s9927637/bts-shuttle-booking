"""
PassengerProfile / PassengerTag — 乘客管理中心資料模型。

PassengerProfile 以 phone 為唯一識別，
所有統計欄位均為從 orders 計算後快取的快照，
透過 passenger_service.sync_passenger(phone) 更新。

不修改 orders 結構，不影響 BTS 訂單。
"""
from datetime import datetime
from app import db

PREDEFINED_TAGS = ["VIP", "高回購", "未付款", "黑名單", "高價值客戶", "常客", "新客"]


class PassengerProfile(db.Model):
    __tablename__ = "passenger_profiles"

    id           = db.Column(db.Integer, primary_key=True)
    name         = db.Column(db.String(100), nullable=False)
    phone        = db.Column(db.String(30),  nullable=False, unique=True, index=True)
    line_user_id = db.Column(db.String(100), nullable=True,  index=True)
    display_name = db.Column(db.String(100), nullable=True)
    total_orders = db.Column(db.Integer, nullable=False, default=0)
    total_events = db.Column(db.Integer, nullable=False, default=0)
    total_spent  = db.Column(db.Integer, nullable=False, default=0)
    last_order_at= db.Column(db.DateTime, nullable=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at   = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tags = db.relationship("PassengerTag", backref="passenger",
                           lazy="dynamic", cascade="all, delete-orphan")

    @property
    def tag_names(self) -> list[str]:
        return [t.tag_name for t in self.tags]

    @property
    def is_vip(self) -> bool:
        return any(t.tag_name == "VIP" for t in self.tags)

    @property
    def is_repurchase(self) -> bool:
        return self.total_orders >= 2

    @property
    def total_spent_fmt(self) -> str:
        return f"NT$ {self.total_spent:,}"


class PassengerTag(db.Model):
    __tablename__ = "passenger_tags"

    id           = db.Column(db.Integer, primary_key=True)
    passenger_id = db.Column(db.Integer,
                             db.ForeignKey("passenger_profiles.id", ondelete="CASCADE"),
                             nullable=False, index=True)
    tag_name     = db.Column(db.String(50), nullable=False, index=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("passenger_id", "tag_name", name="uq_passenger_tag"),
    )
