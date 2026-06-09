from datetime import datetime
from app import db

class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    payer_name = db.Column(db.String(100))
    bank_last5 = db.Column(db.String(5))
    status = db.Column(db.String(20), default="待確認")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
