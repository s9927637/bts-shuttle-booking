"""
SystemHealthCheck — 系統各模組健康狀態紀錄。

每個 component_name 一筆（UPSERT），由 health_check_service 執行後更新。
不影響任何訂單 / 付款 / 收據 / 通知功能。
"""
from datetime import datetime
from app import db

_STATUS_META = {
    "HEALTHY":         ("正常",    "green"),
    "WARNING":         ("警告",    "yellow"),
    "ERROR":           ("異常",    "red"),
    "NOT_IMPLEMENTED": ("未實作",  "gray"),
    "UNKNOWN":         ("未知",    "gray"),
}


class SystemHealthCheck(db.Model):
    __tablename__ = "system_health_checks"

    id              = db.Column(db.Integer,    primary_key=True)
    component_name  = db.Column(db.String(100), nullable=False, unique=True)
    status          = db.Column(db.String(20),  nullable=False, default="UNKNOWN")
    response_time   = db.Column(db.Float,       nullable=True)
    last_checked_at = db.Column(db.DateTime,    nullable=True)
    message         = db.Column(db.Text,        nullable=True)
    created_at      = db.Column(db.DateTime,    default=datetime.utcnow)

    @property
    def status_label(self) -> str:
        return _STATUS_META.get(self.status, ("未知", "gray"))[0]

    @property
    def status_color(self) -> str:
        return _STATUS_META.get(self.status, ("未知", "gray"))[1]

    @property
    def response_time_ms(self) -> str:
        if self.response_time is None:
            return "—"
        return f"{int(self.response_time * 1000)} ms"
