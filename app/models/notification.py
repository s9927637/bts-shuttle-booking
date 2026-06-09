from datetime import datetime
from app import db


class Notification(db.Model):
    __tablename__ = "notifications"

    id            = db.Column(db.Integer, primary_key=True)
    type          = db.Column(db.String(20), nullable=False)   # driver / passenger
    receiver_type = db.Column(db.String(20), nullable=False)   # driver / passenger
    receiver_id   = db.Column(db.String(100))                  # LINE user_id
    receiver_name = db.Column(db.String(100))
    message       = db.Column(db.Text)
    status        = db.Column(db.String(20), default="pending") # success / failed / skipped
    dispatch_id   = db.Column(db.Integer, db.ForeignKey("dispatches.id"), nullable=True)
    order_id      = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
