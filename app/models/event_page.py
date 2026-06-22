from datetime import datetime
from app import db


class EventPage(db.Model):
    __tablename__ = "event_pages"

    id           = db.Column(db.Integer, primary_key=True)
    title        = db.Column(db.String(200), nullable=False)
    slug         = db.Column(db.String(200), nullable=False, unique=True, index=True)
    artist_name  = db.Column(db.String(100), nullable=False)
    event_name   = db.Column(db.String(200), nullable=False)
    event_date   = db.Column(db.String(200), nullable=True)   # 可存多場次文字，例如 "11/19・11/21"
    departure_city = db.Column(db.String(50), nullable=True)
    price        = db.Column(db.Integer, nullable=True, default=2000)
    deposit      = db.Column(db.Integer, nullable=True, default=300)
    cover_image  = db.Column(db.String(500), nullable=True)   # URL
    status       = db.Column(db.String(20), nullable=False, default="草稿")
    description  = db.Column(db.Text, nullable=True)
    faq_content  = db.Column(db.Text, nullable=True)
    terms_content = db.Column(db.Text, nullable=True)
    # 預留未來接入欄位
    # Phase 1：擴充欄位
    category         = db.Column(db.String(50),  nullable=True, default='concert')
    venue            = db.Column(db.String(200),  nullable=True)
    booking_open_at  = db.Column(db.DateTime,     nullable=True)
    booking_close_at = db.Column(db.DateTime,     nullable=True)
    banner_image     = db.Column(db.String(500),  nullable=True)
    thumbnail_image  = db.Column(db.String(500),  nullable=True)
    # Phase 1 V2：主題色
    theme_color      = db.Column(db.String(30),   nullable=True, default='purple')

    concert_id     = db.Column(db.Integer, db.ForeignKey("concerts.id",     ondelete="SET NULL"), nullable=True)
    event_group_id = db.Column(db.Integer, db.ForeignKey("event_groups.id", ondelete="SET NULL"), nullable=True)
    deleted_at   = db.Column(db.DateTime, nullable=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at   = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    concert     = db.relationship("Concert",    foreign_keys=[concert_id],     backref=db.backref("event_pages", lazy="select"))
    event_group = db.relationship("EventGroup", foreign_keys=[event_group_id], backref=db.backref("event_pages", lazy="select"))
    sections    = db.relationship("EventSection", backref="event_page", lazy="dynamic",
                                  cascade="all, delete-orphan", order_by="EventSection.sort_order")

    CATEGORY_LABELS = {
        'concert':    '演唱會',
        'sports':     '球賽',
        'festival':   '節慶',
        'exhibition': '展覽',
        'other':      '其他',
    }

    # 主題色 → CSS hex（fallback 到深紫）
    THEME_CSS = {
        'purple': '#7c3aed',
        'beige':  '#c4a882',
        'pink':   '#ec4899',
        'blue':   '#3b82f6',
        'green':  '#22c55e',
        'red':    '#ef4444',
        'orange': '#f97316',
    }

    @property
    def category_label(self):
        return self.CATEGORY_LABELS.get(self.category or 'concert', '演唱會')

    @property
    def theme_css_color(self):
        return self.THEME_CSS.get(self.theme_color or 'purple', '#7c3aed')

    @property
    def display_image(self):
        return self.banner_image or self.cover_image

    @property
    def event_display_name(self):
        """供 LINE / 收據顯示用的活動名稱"""
        return self.title or self.event_name or f"{self.artist_name} 活動包車"

    @property
    def is_published(self):
        return self.status == "已發布" and self.deleted_at is None

    @property
    def balance(self):
        return (self.price or 0) - (self.deposit or 0)
