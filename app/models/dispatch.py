from datetime import datetime
from app import db


class Dispatch(db.Model):
    __tablename__ = "dispatches"

    id             = db.Column(db.Integer, primary_key=True)
    departure_date = db.Column(db.String(20), nullable=False)
    vehicle_id     = db.Column(db.Integer, db.ForeignKey("vehicles.id"), nullable=False)
    driver_id      = db.Column(db.Integer, db.ForeignKey("drivers.id"), nullable=True)
    status         = db.Column(db.String(20), default="排車中")  # 排車中 / 確認 / 出發 / 完成
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

    vehicle        = db.relationship("Vehicle", backref="dispatches")
    driver         = db.relationship("Driver",  backref="dispatches")
    dispatch_orders = db.relationship("DispatchOrder", backref="dispatch", cascade="all, delete-orphan")


class DispatchOrder(db.Model):
    __tablename__ = "dispatch_orders"

    id          = db.Column(db.Integer, primary_key=True)
    dispatch_id = db.Column(db.Integer, db.ForeignKey("dispatches.id"), nullable=False)
    order_id    = db.Column(db.Integer, db.ForeignKey("orders.id"),     nullable=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    order       = db.relationship("Order", backref="dispatch_orders")
