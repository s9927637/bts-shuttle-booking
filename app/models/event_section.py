import json
from datetime import datetime
from app import db


class EventSection(db.Model):
    __tablename__ = "event_sections"

    # Phase 3: Landing Page Builder — 支援區塊型別
    # 保留舊型別（vehicle_showcase / process / meeting_point / terms）供既有資料相容，
    # 後台「新增區塊」下拉選單只列出 BUILDER_TYPES（spec 指定的 11 種）。
    TYPES = [
        'hero', 'highlights', 'schedule', 'pickup', 'pricing', 'gallery',
        'announcement', 'faq', 'cta', 'sponsor', 'footer',
        # legacy（相容用，不在新增選單顯示）
        'vehicle_showcase', 'process', 'meeting_point', 'terms',
    ]
    BUILDER_TYPES = [
        'hero', 'highlights', 'schedule', 'pickup', 'pricing', 'gallery',
        'announcement', 'faq', 'cta', 'sponsor', 'footer',
    ]
    TYPE_LABELS = {
        'hero':             'Hero',
        'highlights':       'Highlights',
        'schedule':         'Schedule',
        'pickup':           'Pickup',
        'pricing':          'Pricing',
        'gallery':          'Gallery',
        'announcement':     'Announcement',
        'faq':              'FAQ',
        'cta':              'CTA',
        'sponsor':          'Sponsor',
        'footer':           'Footer',
        'vehicle_showcase': '車型介紹（Legacy）',
        'process':          '流程說明（Legacy）',
        'meeting_point':    '集合地點（Legacy）',
        'terms':            '注意事項（Legacy）',
    }
    THEME_STYLES = ['default', 'primary', 'secondary', 'transparent']
    THEME_STYLE_LABELS = {
        'default':     'Default',
        'primary':     'Primary',
        'secondary':   'Secondary',
        'transparent': 'Transparent',
    }
    TYPE_DEFAULTS = {
        'hero': {
            'title': '包車直達',
            'subtitle': '台北直達高雄',
            'buttonText': '立即預約',
        },
        'highlights': {
            'columns': 3,
            'items': [
                {'icon': '🚗', 'title': '舒適直達', 'description': '免轉乘，一車到底'},
                {'icon': '🕐', 'title': '散場接送', 'description': '演出結束準時發車'},
                {'icon': '👥', 'title': '專屬車隊', 'description': '同好共乘更安心'},
            ],
        },
        'schedule': {
            'event_date':  '',
            'meet_time':   '',
            'depart_time': '',
            'end_time':    '',
        },
        'pickup': {
            'address': '',
            'point':   '',
            'map_url': '',
        },
        'pricing': {
            'price':   None,
            'deposit': None,
            'balance': None,
        },
        'gallery': {
            'images':  [],
            'youtube': '',
        },
        'process': {
            'steps': ['提交預約', '支付訂金', '等待成團', '出發通知'],
        },
        'announcement': {
            'limit': 5,
        },
        'faq': {
            'items': [],
        },
        'cta': {
            'title': '準備好出發了嗎？',
            'buttonText': '立即預約',
        },
        'sponsor': {
            'logos': [],
        },
        'footer': {
            'text': '',
        },
    }

    id           = db.Column(db.Integer, primary_key=True)
    event_id     = db.Column(db.Integer, db.ForeignKey('event_pages.id', ondelete='CASCADE'),
                             nullable=False, index=True)
    type         = db.Column(db.String(50),  nullable=False)
    title        = db.Column(db.String(200), nullable=True)
    content_json = db.Column(db.Text,        nullable=True)
    sort_order   = db.Column(db.Integer,     nullable=False, default=0)
    is_active    = db.Column(db.Boolean,     nullable=False, default=True)
    # Phase 3: 響應式顯示（每個 breakpoint 獨立控制，nullable + 預設 True 向前相容）
    show_desktop = db.Column(db.Boolean,     nullable=True, default=True)
    show_tablet  = db.Column(db.Boolean,     nullable=True, default=True)
    show_mobile  = db.Column(db.Boolean,     nullable=True, default=True)
    # Phase 3: 區塊主題（default/primary/secondary/transparent）
    theme_style  = db.Column(db.String(20),  nullable=True, default='default')
    created_at   = db.Column(db.DateTime,    default=datetime.utcnow)
    updated_at   = db.Column(db.DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def content(self):
        if self.content_json:
            try:
                return json.loads(self.content_json)
            except Exception:
                return {}
        return {}

    @content.setter
    def content(self, value):
        self.content_json = json.dumps(value, ensure_ascii=False)

    @property
    def type_label(self):
        return self.TYPE_LABELS.get(self.type, self.type)

    @property
    def theme_style_resolved(self):
        return self.theme_style or 'default'

    @property
    def visible_desktop(self):
        return self.show_desktop is not False

    @property
    def visible_tablet(self):
        return self.show_tablet is not False

    @property
    def visible_mobile(self):
        return self.show_mobile is not False
