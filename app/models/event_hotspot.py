from datetime import datetime
from app import db


class EventHotspot(db.Model):
    """
    V1 Landing Page：圖片上的可點擊熱點區域。
    座標一律以「容器百分比」儲存（0-100），確保 Desktop/Tablet/Mobile
    三種圖片各自 Responsive 縮放時，熱點位置仍能對齊。
    """
    __tablename__ = "event_hotspots"

    DEVICES = ['desktop', 'tablet', 'mobile']
    DEVICE_LABELS = {'desktop': 'Desktop', 'tablet': 'Tablet', 'mobile': 'Mobile'}

    LINK_TYPES = ['booking', 'orders', 'remittance', 'news', 'faq', 'line', 'custom']
    LINK_TYPE_LABELS = {
        'booking':    '立即預約',
        'orders':     '查詢訂單',
        'remittance': '匯款回報',
        'news':       '最新公告',
        'faq':        'FAQ',
        'line':       'LINE 官方帳號',
        'custom':     '自訂連結',
    }

    id         = db.Column(db.Integer, primary_key=True)
    event_id   = db.Column(db.Integer, db.ForeignKey('event_pages.id', ondelete='CASCADE'),
                           nullable=False, index=True)
    # Bug Fix Phase 1: Desktop/Tablet/Mobile 各自獨立一組 Hotspot，不再共用
    device     = db.Column(db.String(10), nullable=False, default='desktop')
    label      = db.Column(db.String(100), nullable=False)
    link_type  = db.Column(db.String(20), nullable=False, default='booking')
    custom_url = db.Column(db.String(500), nullable=True)   # 僅 link_type == 'custom' 時使用

    # 座標與尺寸：容器百分比（0-100）
    x_pct = db.Column(db.Float, nullable=False, default=10.0)
    y_pct = db.Column(db.Float, nullable=False, default=10.0)
    w_pct = db.Column(db.Float, nullable=False, default=20.0)
    h_pct = db.Column(db.Float, nullable=False, default=10.0)

    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active  = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def link_type_label(self):
        return self.LINK_TYPE_LABELS.get(self.link_type, self.link_type)

    def resolved_url(self, ep, line_url=None):
        """依 link_type 解析出實際連結網址。ep 為所屬 EventPage。"""
        slug = ep.slug
        if self.link_type == 'booking':
            return f"/events/{slug}/booking"
        if self.link_type == 'orders':
            return f"/events/{slug}/orders"
        if self.link_type == 'remittance':
            return f"/events/{slug}/remittance"
        if self.link_type == 'news':
            return f"/events/{slug}/news"
        if self.link_type == 'faq':
            return f"/events/{slug}/faq"
        if self.link_type == 'line':
            return line_url or self.custom_url or '#'
        return self.custom_url or '#'

    @property
    def opens_new_tab(self):
        return self.link_type == 'line'
