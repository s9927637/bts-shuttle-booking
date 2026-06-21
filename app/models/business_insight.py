"""
BusinessInsight — 演唱會商機決策資料。

每筆 ConcertDataHub 對應一筆 BusinessInsight。
由 Business Intelligence Engine 計算並寫入。
"""
from datetime import datetime
from app import db

_RECOMMENDATION_LABELS = {
    "STRONGLY_RECOMMENDED": ("強烈推薦", "green"),
    "RECOMMENDED":          ("推薦",     "blue"),
    "OBSERVE":              ("觀望",     "yellow"),
    "NOT_RECOMMENDED":      ("不推薦",   "red"),
}

_RISK_LABELS = {
    "LOW":    ("低",   "green"),
    "MEDIUM": ("中",   "yellow"),
    "HIGH":   ("高",   "red"),
}


class BusinessInsight(db.Model):
    __tablename__ = "business_insights"

    id                  = db.Column(db.Integer,   primary_key=True)
    concert_hub_id      = db.Column(db.Integer,   db.ForeignKey("concert_data_hub.id", ondelete="CASCADE"), nullable=False, index=True)

    opportunity_score   = db.Column(db.Integer,   nullable=False, default=0)
    demand_score        = db.Column(db.Integer,   nullable=False, default=0)
    historical_score    = db.Column(db.Integer,   nullable=False, default=0)
    competition_score   = db.Column(db.Integer,   nullable=False, default=0)
    profitability_score = db.Column(db.Integer,   nullable=False, default=0)

    estimated_passengers = db.Column(db.Integer,  nullable=False, default=0)
    estimated_vehicles   = db.Column(db.Integer,  nullable=False, default=0)
    estimated_revenue    = db.Column(db.Integer,  nullable=False, default=0)
    estimated_profit     = db.Column(db.Integer,  nullable=False, default=0)

    recommendation      = db.Column(db.String(30), nullable=False, default="OBSERVE")
    risk_level          = db.Column(db.String(20), nullable=False, default="MEDIUM")
    notes               = db.Column(db.Text,       nullable=True)

    created_at          = db.Column(db.DateTime,  default=datetime.utcnow)
    updated_at          = db.Column(db.DateTime,  default=datetime.utcnow, onupdate=datetime.utcnow)

    hub = db.relationship("ConcertDataHub", foreign_keys=[concert_hub_id],
                          backref=db.backref("insight", uselist=False))

    # ── 顯示屬性 ─────────────────────────────────────────────────────────────

    @property
    def recommendation_label(self) -> str:
        return _RECOMMENDATION_LABELS.get(self.recommendation, ("—", "gray"))[0]

    @property
    def recommendation_color(self) -> str:
        return _RECOMMENDATION_LABELS.get(self.recommendation, ("—", "gray"))[1]

    @property
    def risk_label(self) -> str:
        return _RISK_LABELS.get(self.risk_level, ("—", "gray"))[0]

    @property
    def risk_color(self) -> str:
        return _RISK_LABELS.get(self.risk_level, ("—", "gray"))[1]

    @property
    def estimated_revenue_fmt(self) -> str:
        return f"NT${self.estimated_revenue:,}"

    @property
    def estimated_profit_fmt(self) -> str:
        return f"NT${self.estimated_profit:,}"
