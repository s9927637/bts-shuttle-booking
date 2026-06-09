from datetime import datetime
from app import db

class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    order_no = db.Column(db.String(30), unique=True, nullable=False)
    contact_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    emergency_phone = db.Column(db.String(20))
    departure_date = db.Column(db.String(20), nullable=False)
    passenger_count = db.Column(db.Integer, nullable=False)
    companion_names = db.Column(db.Text)
    remark = db.Column(db.Text)
    total_amount    = db.Column(db.Integer, nullable=False)
    deposit_amount  = db.Column(db.Integer, nullable=False, default=0)
    balance_amount  = db.Column(db.Integer, nullable=False, default=0)
    payment_status  = db.Column(db.String(20), default="待付款")
    vehicle_id   = db.Column(db.Integer, db.ForeignKey("vehicles.id"))
    dispatch_id  = db.Column(db.Integer, db.ForeignKey("dispatches.id"), nullable=True)
    line_user_id = db.Column(db.String(50), nullable=True, index=True)
    display_name = db.Column(db.String(100), nullable=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
