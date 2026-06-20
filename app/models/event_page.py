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
    concert_id     = db.Column(db.Integer, db.ForeignKey("concerts.id",     ondelete="SET NULL"), nullable=True)
    event_group_id = db.Column(db.Integer, db.ForeignKey("event_groups.id", ondelete="SET NULL"), nullable=True)
    deleted_at   = db.Column(db.DateTime, nullable=True)   # 軟刪除
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at   = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    concert     = db.relationship("Concert",    foreign_keys=[concert_id],     backref=db.backref("event_pages", lazy="select"))
    event_group = db.relationship("EventGroup", foreign_keys=[event_group_id], backref=db.backref("event_pages", lazy="select"))

    @property
    def is_published(self):
        return self.status == "已發布" and self.deleted_at is None

    @property
    def balance(self):
        return (self.price or 0) - (self.deposit or 0)
