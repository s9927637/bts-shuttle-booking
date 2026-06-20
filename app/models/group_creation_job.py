from datetime import datetime
from app import db


class GroupCreationJob(db.Model):
    __tablename__ = "group_creation_jobs"

    id             = db.Column(db.Integer, primary_key=True)
    concert_id     = db.Column(db.Integer, db.ForeignKey("concerts.id",               ondelete="SET NULL"), nullable=True,  index=True)
    opportunity_id = db.Column(db.Integer, db.ForeignKey("concert_opportunities.id",  ondelete="SET NULL"), nullable=True)
    event_page_id  = db.Column(db.Integer, db.ForeignKey("event_pages.id",            ondelete="SET NULL"), nullable=True,  index=True)
    template_id    = db.Column(db.Integer, db.ForeignKey("event_templates.id",        ondelete="SET NULL"), nullable=True)
    status         = db.Column(db.String(20), nullable=False, default="pending")
    error_message  = db.Column(db.Text,    nullable=True)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at     = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    concert     = db.relationship("Concert",             foreign_keys=[concert_id],     backref=db.backref("creation_jobs", lazy="dynamic"))
    opportunity = db.relationship("ConcertOpportunity",  foreign_keys=[opportunity_id], backref=db.backref("creation_jobs", lazy="dynamic"))
    event_page  = db.relationship("EventPage",           foreign_keys=[event_page_id],  backref=db.backref("creation_job",  uselist=False))
    template    = db.relationship("EventTemplate",       foreign_keys=[template_id],    backref=db.backref("creation_jobs", lazy="dynamic"))
