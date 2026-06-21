"""
ConcertDataHub — 統一演唱會資料池。

整合 KKTIX + TixCraft 的資料，計算可信度分數，
作為商機分析 / 自動開團的唯一資料來源。
"""
from datetime import datetime
from app import db


class ConcertDataHub(db.Model):
    __tablename__ = "concert_data_hub"

    id               = db.Column(db.Integer,     primary_key=True)
    concert_id       = db.Column(db.Integer,     db.ForeignKey("concerts.id", ondelete="SET NULL"), nullable=True, index=True)
    artist_name      = db.Column(db.String(100), nullable=False)
    concert_name     = db.Column(db.String(200), nullable=False)
    event_date       = db.Column(db.Date,        nullable=True)
    venue            = db.Column(db.String(200), nullable=True)
    city             = db.Column(db.String(50),  nullable=True)
    ticket_sale_date = db.Column(db.String(100), nullable=True)
    source_count     = db.Column(db.Integer,     nullable=False, default=0)
    source_types     = db.Column(db.String(100), nullable=True)
    source_urls      = db.Column(db.Text,        nullable=True)
    confidence_score = db.Column(db.Integer,     nullable=False, default=0)
    status           = db.Column(db.String(20),  nullable=False, default="active")
    has_conflict     = db.Column(db.Boolean,     nullable=False, default=False)
    conflict_types   = db.Column(db.String(200), nullable=True)
    created_at       = db.Column(db.DateTime,    default=datetime.utcnow)
    updated_at       = db.Column(db.DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)

    concert = db.relationship("Concert", foreign_keys=[concert_id])

    @property
    def confidence_label(self) -> str:
        if self.confidence_score >= 80:
            return "高"
        elif self.confidence_score >= 50:
            return "中"
        return "低"

    @property
    def confidence_color(self) -> str:
        if self.confidence_score >= 80:
            return "green"
        elif self.confidence_score >= 50:
            return "yellow"
        return "red"

    @property
    def source_type_list(self) -> list[str]:
        if not self.source_types:
            return []
        return [s.strip() for s in self.source_types.split(",") if s.strip()]
