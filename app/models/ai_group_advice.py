"""
AiGroupAdvice — AI 開團顧問建議資料。

每筆 ConcertDataHub 對應一筆建議（INSERT OR UPDATE）。
由 group_advisor_service 計算，不直接建立活動。
"""
from datetime import datetime
from app import db

_RISK_LABELS = {
    "LOW":    "低",
    "MEDIUM": "中",
    "HIGH":   "高",
}

_RISK_COLORS = {
    "LOW":    "green",
    "MEDIUM": "yellow",
    "HIGH":   "red",
}


class AiGroupAdvice(db.Model):
    __tablename__ = "ai_group_advice"

    id                          = db.Column(db.Integer,   primary_key=True)
    concert_hub_id              = db.Column(db.Integer,   db.ForeignKey("concert_data_hub.id",   ondelete="CASCADE"),   nullable=False, index=True)
    business_insight_id         = db.Column(db.Integer,   db.ForeignKey("business_insights.id",  ondelete="SET NULL"),  nullable=True)

    recommended_price           = db.Column(db.Integer,   nullable=False, default=2000)
    recommended_deposit         = db.Column(db.Integer,   nullable=False, default=300)
    recommended_departure_city  = db.Column(db.String(50), nullable=True)
    recommended_vehicle_count   = db.Column(db.Integer,   nullable=False, default=1)
    recommended_passenger_count = db.Column(db.Integer,   nullable=False, default=0)

    risk_level                  = db.Column(db.String(20), nullable=False, default="MEDIUM")
    confidence_score            = db.Column(db.Integer,   nullable=False, default=0)
    summary                     = db.Column(db.Text,      nullable=True)

    created_at                  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at                  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    hub     = db.relationship("ConcertDataHub", foreign_keys=[concert_hub_id],
                              backref=db.backref("advice", uselist=False))
    insight = db.relationship("BusinessInsight", foreign_keys=[business_insight_id])

    @property
    def risk_label(self) -> str:
        return _RISK_LABELS.get(self.risk_level, "—")

    @property
    def risk_color(self) -> str:
        return _RISK_COLORS.get(self.risk_level, "gray")

    @property
    def recommended_price_fmt(self) -> str:
        return f"NT${self.recommended_price:,}"

    @property
    def recommended_deposit_fmt(self) -> str:
        return f"NT${self.recommended_deposit:,}"

    @property
    def confidence_label(self) -> str:
        if self.confidence_score >= 80:
            return "高"
        elif self.confidence_score >= 50:
            return "中"
        return "低"
