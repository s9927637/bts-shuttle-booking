from datetime import datetime
from app import db


class CrawlJob(db.Model):
    __tablename__ = "crawl_jobs"

    id              = db.Column(db.Integer, primary_key=True)
    source_name     = db.Column(db.String(100), nullable=False)
    status          = db.Column(db.String(20),  nullable=False, default="pending")
    started_at      = db.Column(db.DateTime, nullable=True)
    finished_at     = db.Column(db.DateTime, nullable=True)
    created_count   = db.Column(db.Integer, nullable=False, default=0)
    updated_count   = db.Column(db.Integer, nullable=False, default=0)
    skipped_count   = db.Column(db.Integer, nullable=False, default=0)
    error_count     = db.Column(db.Integer, nullable=False, default=0)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    # 預留欄位供未來排程使用
    scheduler_enabled = db.Column(db.Boolean, nullable=False, default=False)
    last_success_at   = db.Column(db.DateTime, nullable=True)

    logs = db.relationship("CrawlLog", back_populates="job",
                           cascade="all, delete-orphan",
                           order_by="CrawlLog.created_at")

    @property
    def duration_seconds(self):
        if self.started_at and self.finished_at:
            return int((self.finished_at - self.started_at).total_seconds())
        return None

    @property
    def is_running(self):
        return self.status == "running"
