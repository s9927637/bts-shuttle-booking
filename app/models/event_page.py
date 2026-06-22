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
    # Phase 2：活動特色欄位（Hero 4格）
    subtitle         = db.Column(db.String(200),  nullable=True)
    feat1_title      = db.Column(db.String(60),   nullable=True, default='專屬包車')
    feat1_sub        = db.Column(db.String(80),   nullable=True, default='直達會場')
    feat2_title      = db.Column(db.String(60),   nullable=True, default='舒適乘坐')
    feat2_sub        = db.Column(db.String(80),   nullable=True, default='旅遊艙款')
    feat3_title      = db.Column(db.String(60),   nullable=True, default='準時接送')
    feat3_sub        = db.Column(db.String(80),   nullable=True, default='不超行程')
    feat4_title      = db.Column(db.String(60),   nullable=True, default='安全安心')
    feat4_sub        = db.Column(db.String(80),   nullable=True, default='專業司機')

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

    # 主題色 → CSS hex（fallback 到深紫，向前相容用）
    THEME_CSS = {
        'purple': '#7c3aed',
        'beige':  '#c4a882',
        'pink':   '#ec4899',
        'blue':   '#3b82f6',
        'green':  '#22c55e',
        'red':    '#ef4444',
        'orange': '#f97316',
    }

    # 完整 theme token 系統
    THEME_TOKENS = {
        'purple': {
            'primary':      '#7c3aed',
            'secondary':    '#a855f7',
            'accent':       '#c4b5fd',
            'text_accent':  '#e9d5ff',
            'muted':        '#a78bfa',
            'overlay_rgb':  '88,28,135',
            'card_bg':      'rgba(124,58,237,0.12)',
            'icon_bg':      'rgba(139,92,246,0.22)',
            'gradient':     'linear-gradient(135deg, #7c3aed 0%, #9333ea 100%)',
            'shadow':       'rgba(124,58,237,0.45)',
        },
        'beige': {
            'primary':      '#b08968',
            'secondary':    '#c4a882',
            'accent':       '#e6d5c3',
            'text_accent':  '#fdf8f0',
            'muted':        '#c4a882',
            'overlay_rgb':  '139,109,80',
            'card_bg':      'rgba(176,137,104,0.12)',
            'icon_bg':      'rgba(196,168,130,0.22)',
            'gradient':     'linear-gradient(135deg, #b08968 0%, #c4a882 100%)',
            'shadow':       'rgba(176,137,104,0.45)',
        },
        'pink': {
            'primary':      '#ec4899',
            'secondary':    '#f472b6',
            'accent':       '#fce7f3',
            'text_accent':  '#fdf2f8',
            'muted':        '#f9a8d4',
            'overlay_rgb':  '190,24,93',
            'card_bg':      'rgba(236,72,153,0.12)',
            'icon_bg':      'rgba(244,114,182,0.22)',
            'gradient':     'linear-gradient(135deg, #ec4899 0%, #f472b6 100%)',
            'shadow':       'rgba(236,72,153,0.45)',
        },
        'blue': {
            'primary':      '#3b82f6',
            'secondary':    '#60a5fa',
            'accent':       '#bfdbfe',
            'text_accent':  '#eff6ff',
            'muted':        '#93c5fd',
            'overlay_rgb':  '37,99,235',
            'card_bg':      'rgba(59,130,246,0.12)',
            'icon_bg':      'rgba(96,165,250,0.22)',
            'gradient':     'linear-gradient(135deg, #3b82f6 0%, #6366f1 100%)',
            'shadow':       'rgba(59,130,246,0.45)',
        },
        'green': {
            'primary':      '#22c55e',
            'secondary':    '#4ade80',
            'accent':       '#bbf7d0',
            'text_accent':  '#f0fdf4',
            'muted':        '#86efac',
            'overlay_rgb':  '21,128,61',
            'card_bg':      'rgba(34,197,94,0.12)',
            'icon_bg':      'rgba(74,222,128,0.22)',
            'gradient':     'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)',
            'shadow':       'rgba(34,197,94,0.45)',
        },
        'red': {
            'primary':      '#ef4444',
            'secondary':    '#f87171',
            'accent':       '#fecaca',
            'text_accent':  '#fef2f2',
            'muted':        '#fca5a5',
            'overlay_rgb':  '185,28,28',
            'card_bg':      'rgba(239,68,68,0.12)',
            'icon_bg':      'rgba(248,113,113,0.22)',
            'gradient':     'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
            'shadow':       'rgba(239,68,68,0.45)',
        },
        'orange': {
            'primary':      '#f97316',
            'secondary':    '#fb923c',
            'accent':       '#fed7aa',
            'text_accent':  '#fff7ed',
            'muted':        '#fdba74',
            'overlay_rgb':  '194,65,12',
            'card_bg':      'rgba(249,115,22,0.12)',
            'icon_bg':      'rgba(251,146,60,0.22)',
            'gradient':     'linear-gradient(135deg, #f97316 0%, #ea580c 100%)',
            'shadow':       'rgba(249,115,22,0.45)',
        },
    }

    @property
    def category_label(self):
        return self.CATEGORY_LABELS.get(self.category or 'concert', '演唱會')

    @property
    def theme_css_color(self):
        return self.THEME_CSS.get(self.theme_color or 'purple', '#7c3aed')

    @property
    def theme_tokens(self) -> dict:
        return self.THEME_TOKENS.get(self.theme_color or 'purple', self.THEME_TOKENS['purple'])

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
