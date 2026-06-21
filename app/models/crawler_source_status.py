"""
CrawlerSourceStatus — 各資料來源爬蟲覆蓋率狀態。

每個來源一筆，由 coverage_service 定期刷新。
不影響任何訂單 / 付款 / 收據功能。
"""
from datetime import datetime
from app import db

_COVERAGE_LABELS = {
    "FULL":    ("完整", "green"),
    "PARTIAL": ("部分", "yellow"),
    "NONE":    ("未抓", "red"),
}


class CrawlerSourceStatus(db.Model):
    __tablename__ = "crawler_source_status"

    id              = db.Column(db.Integer,    primary_key=True)
    source_name     = db.Column(db.String(100), nullable=False, unique=True)
    crawler_enabled = db.Column(db.Boolean,    nullable=False, default=False)
    last_run_at     = db.Column(db.DateTime,   nullable=True)
    raw_count       = db.Column(db.Integer,    nullable=False, default=0)
    imported_count  = db.Column(db.Integer,    nullable=False, default=0)
    skipped_count   = db.Column(db.Integer,    nullable=False, default=0)
    coverage_status = db.Column(db.String(20), nullable=False, default="NONE")
    created_at      = db.Column(db.DateTime,   default=datetime.utcnow)
    updated_at      = db.Column(db.DateTime,   default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def coverage_label(self) -> str:
        return _COVERAGE_LABELS.get(self.coverage_status, ("未知", "gray"))[0]

    @property
    def coverage_color(self) -> str:
        return _COVERAGE_LABELS.get(self.coverage_status, ("未知", "gray"))[1]

    @property
    def coverage_pct(self) -> int:
        """匯入率百分比（0–100）。"""
        if not self.raw_count:
            return 0
        return min(int(self.imported_count / self.raw_count * 100), 100)
