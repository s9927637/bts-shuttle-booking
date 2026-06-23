from datetime import datetime
from app import db


class Announcement(db.Model):
    __tablename__ = "announcements"

    id                = db.Column(db.Integer, primary_key=True)
    title             = db.Column(db.String(255), nullable=False)
    content           = db.Column(db.Text, nullable=False)
    announcement_type = db.Column(db.String(20), nullable=False, default="一般公告")
    status            = db.Column(db.String(20), nullable=False, default="草稿")
    is_pinned         = db.Column(db.Boolean, nullable=False, default=False)
    publish_to_line   = db.Column(db.Boolean, nullable=False, default=False)
    line_target       = db.Column(db.String(50), nullable=True)
    created_at        = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at        = db.Column(db.DateTime, nullable=True, onupdate=datetime.utcnow)

    # 活動隔離：NULL = 全站公告（BTS 相容）
    event_page_id = db.Column(
        db.Integer,
        db.ForeignKey("event_pages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_page = db.relationship(
        "EventPage",
        foreign_keys=[event_page_id],
        backref=db.backref("announcements", lazy="dynamic"),
    )
