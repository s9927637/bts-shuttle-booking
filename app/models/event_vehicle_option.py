from datetime import datetime
from app import db

PRICING_MODES = ['event_price', 'fixed', 'markup']
PRICING_MODE_LABELS = {
    'event_price': '使用活動價格',
    'fixed': '固定價格',
    'markup': '加價',
}

# 建立活動時預設建立的車輛方案（④ 九座商旅車為預設選中方案）
DEFAULT_VEHICLE_OPTIONS = [
    {"name": "一般轎車",   "capacity": 4},
    {"name": "豪華轎車",   "capacity": 4},
    {"name": "七人座休旅", "capacity": 6},
    {"name": "九座商旅車", "capacity": 8, "is_default": True},
    {"name": "尊榮商務",   "capacity": 6},
    {"name": "保母車",     "capacity": 8},
    {"name": "中型巴士",   "capacity": 20},
    {"name": "大型遊覽車", "capacity": 43},
]


class EventVehicleOption(db.Model):
    __tablename__ = "event_vehicle_options"

    id       = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("event_pages.id", ondelete="CASCADE"), nullable=False, index=True)

    name            = db.Column(db.String(100), nullable=False)
    description     = db.Column(db.String(255), nullable=True)
    example_models  = db.Column(db.String(500), nullable=True)   # 逗號分隔，例：Toyota Alphard,Lexus LM
    capacity        = db.Column(db.Integer, nullable=False, default=4)
    image           = db.Column(db.String(500), nullable=True)

    # 價格模式：event_price（使用活動價格，預設）／fixed（固定價格）／markup（加價）
    pricing_mode      = db.Column(db.String(20), nullable=False, default="event_price")
    price             = db.Column(db.Integer, nullable=True)   # pricing_mode == 'fixed' 時使用
    price_adjustment  = db.Column(db.Integer, nullable=True)   # pricing_mode == 'markup' 時使用（+$）

    badge      = db.Column(db.String(50), nullable=True)       # 推薦標籤，例：👑 尊榮推薦
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_default = db.Column(db.Boolean, nullable=False, default=False)  # 預約頁預設選中
    is_visible = db.Column(db.Boolean, nullable=False, default=True)   # 前台顯示
    is_active  = db.Column(db.Boolean, nullable=False, default=True)   # 啟用（停用僅隱藏，不刪除既有訂單關聯）

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    event_page = db.relationship(
        "EventPage",
        backref=db.backref("vehicle_options", cascade="all, delete-orphan", lazy="dynamic",
                            order_by="EventVehicleOption.sort_order"),
    )

    @property
    def example_models_list(self):
        return [m.strip() for m in (self.example_models or "").split(",") if m.strip()]

    @property
    def pricing_mode_label(self):
        return PRICING_MODE_LABELS.get(self.pricing_mode, self.pricing_mode)
