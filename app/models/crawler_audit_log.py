from datetime import datetime
from app import db


class CrawlerAuditLog(db.Model):
    __tablename__ = "crawler_audit_logs"

    id          = db.Column(db.Integer, primary_key=True)
    job_id      = db.Column(db.Integer, db.ForeignKey("crawl_jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    source_name = db.Column(db.String(50),  nullable=False, index=True)
    event_name  = db.Column(db.String(300), nullable=True)
    artist_name = db.Column(db.String(150), nullable=True)
    event_date  = db.Column(db.Date(),      nullable=True)
    venue       = db.Column(db.String(200), nullable=True)
    city        = db.Column(db.String(50),  nullable=True)
    source_url  = db.Column(db.String(500), nullable=True)
    # Status: CRAWLED / PARSED / VALIDATED / IMPORTED / SKIPPED
    status      = db.Column(db.String(20),  nullable=False, index=True)
    # Reason: DATE_MISSING / ARTIST_MISSING / VENUE_MISSING / PAST_EVENT /
    #         DUPLICATE / INVALID_FORMAT / IMPORT_ERROR
    reason      = db.Column(db.String(50),  nullable=True,  index=True)
    created_at  = db.Column(db.DateTime(),  default=datetime.utcnow, index=True)

    STATUS_CRAWLED   = "CRAWLED"
    STATUS_PARSED    = "PARSED"
    STATUS_VALIDATED = "VALIDATED"
    STATUS_IMPORTED  = "IMPORTED"
    STATUS_SKIPPED   = "SKIPPED"

    REASON_DATE_MISSING    = "DATE_MISSING"
    REASON_ARTIST_MISSING  = "ARTIST_MISSING"
    REASON_VENUE_MISSING   = "VENUE_MISSING"
    REASON_PAST_EVENT      = "PAST_EVENT"
    REASON_DUPLICATE       = "DUPLICATE"
    REASON_INVALID_FORMAT  = "INVALID_FORMAT"
    REASON_IMPORT_ERROR    = "IMPORT_ERROR"

    @property
    def status_color(self) -> str:
        return {
            "CRAWLED":   "gray",
            "PARSED":    "indigo",
            "VALIDATED": "blue",
            "IMPORTED":  "green",
            "SKIPPED":   "red",
        }.get(self.status, "gray")

    @property
    def reason_label(self) -> str:
        return {
            "DATE_MISSING":   "缺少日期",
            "ARTIST_MISSING": "缺少藝人",
            "VENUE_MISSING":  "缺少場館",
            "PAST_EVENT":     "歷史活動",
            "DUPLICATE":      "重複資料",
            "INVALID_FORMAT": "格式錯誤",
            "IMPORT_ERROR":   "匯入錯誤",
        }.get(self.reason or "", self.reason or "—")
