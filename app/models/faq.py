from datetime import datetime
from app import db


class Faq(db.Model):
    __tablename__ = "faqs"

    id            = db.Column(db.Integer, primary_key=True)
    question      = db.Column(db.String(500), nullable=False)
    answer        = db.Column(db.Text, nullable=False)
    sort_order    = db.Column(db.Integer, nullable=False, default=0)
    is_active     = db.Column(db.Boolean, nullable=False, default=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime, nullable=True, onupdate=datetime.utcnow)

    event_page_id = db.Column(
        db.Integer,
        db.ForeignKey("event_pages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_page = db.relationship(
        "EventPage",
        foreign_keys=[event_page_id],
        backref=db.backref("faqs", lazy="dynamic", order_by="Faq.sort_order"),
    )
