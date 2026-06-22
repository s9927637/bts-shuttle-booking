import json
from datetime import datetime
from app import db


SECTION_TYPES = [
    'hero', 'highlights', 'vehicle_showcase', 'process',
    'meeting_point', 'faq', 'terms', 'cta', 'footer',
]
SECTION_TYPE_LABELS = {
    'hero':             'Hero Banner',
    'highlights':       '服務特色',
    'vehicle_showcase': '車型介紹',
    'process':          '預約流程',
    'meeting_point':    '集合地點',
    'faq':              '常見問題',
    'terms':            '注意事項',
    'cta':              '立即預約',
    'footer':           '頁尾',
}


class ActivityTemplate(db.Model):
    __tablename__ = 'activity_templates'

    id          = db.Column(db.Integer,     primary_key=True)
    name        = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text,        nullable=True)
    theme_color = db.Column(db.String(30),  nullable=True, default='purple')
    is_default  = db.Column(db.Boolean,     nullable=False, default=False)
    created_at  = db.Column(db.DateTime,    default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)

    sections = db.relationship(
        'ActivityTemplateSection',
        backref='template',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='ActivityTemplateSection.sort_order',
    )

    @property
    def section_count(self) -> int:
        return self.sections.count()


class ActivityTemplateSection(db.Model):
    __tablename__ = 'activity_template_sections'

    id           = db.Column(db.Integer,     primary_key=True)
    template_id  = db.Column(db.Integer,
                             db.ForeignKey('activity_templates.id', ondelete='CASCADE'),
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
    def type_label(self) -> str:
        return SECTION_TYPE_LABELS.get(self.type, self.type)
