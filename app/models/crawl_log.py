from datetime import datetime
from app import db


class CrawlLog(db.Model):
    __tablename__ = "crawl_logs"

    id          = db.Column(db.Integer, primary_key=True)
    job_id      = db.Column(db.Integer, db.ForeignKey("crawl_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    source_name = db.Column(db.String(100), nullable=False)
    level       = db.Column(db.String(10),  nullable=False, default="INFO")
    message     = db.Column(db.Text, nullable=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    job = db.relationship("CrawlJob", back_populates="logs")
