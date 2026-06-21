import json
from datetime import datetime
from app import db


class EventSection(db.Model):
    __tablename__ = "event_sections"

    TYPES = ['hero', 'highlights', 'process', 'announcement', 'faq', 'cta']
    TYPE_LABELS = {
        'hero':         'Hero 橫幅',
        'highlights':   '特色亮點',
        'process':      '流程說明',
        'announcement': '公告',
        'faq':          '常見問題',
        'cta':          '行動呼籲',
    }
    TYPE_DEFAULTS = {
        'hero': {
            'title': '包車直達',
            'subtitle': '台北直達高雄',
            'buttonText': '立即預約',
        },
        'highlights': {
            'items': ['舒適直達', '散場接送', '專屬車隊'],
        },
        'process': {
            'steps': ['提交預約', '支付訂金', '等待成團', '出發通知'],
        },
        'announcement': {
            'content': '注意事項請詳閱',
        },
        'faq': {
            'items': [{'question': '散場多久發車？', 'answer': '依現場狀況安排'}],
        },
        'cta': {
            'title': '準備好出發了嗎？',
            'buttonText': '立即預約',
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
