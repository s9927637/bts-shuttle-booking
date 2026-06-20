from datetime import datetime
from app import db


class EventTemplate(db.Model):
    __tablename__ = "event_templates"

    id             = db.Column(db.Integer, primary_key=True)
    template_name  = db.Column(db.String(100), nullable=False)
    departure_city = db.Column(db.String(50),  nullable=True)
    price          = db.Column(db.Integer,     nullable=False, default=2000)
    deposit        = db.Column(db.Integer,     nullable=False, default=300)
    status         = db.Column(db.String(20),  nullable=False, default="啟用")
    created_at     = db.Column(db.DateTime,    default=datetime.utcnow)

    @property
    def balance(self) -> int:
        return self.price - self.deposit
