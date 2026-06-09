from datetime import datetime
from app import db


class Notification(db.Model):
    __tablename__ = "notifications"

    id                = db.Column(db.Integer, primary_key=True)
    notification_type = db.Column(db.String(50), nullable=False)  # driver / passenger
    recipient_name    = db.Column(db.String(100))
    recipient_id      = db.Column(db.String(100))   # LINE user_id
    dispatch_id       = db.Column(db.Integer, db.ForeignKey("dispatches.id"), nullable=True)
    order_id          = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=True)
    status            = db.Column(db.String(20), default="pending")  # success / failed / skipped
    content           = db.Column(db.Text)
    created_at        = db.Column(db.DateTime, default=datetime.utcnow)
