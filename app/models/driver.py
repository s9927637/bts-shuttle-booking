from datetime import datetime
from app import db


class Driver(db.Model):
    __tablename__ = "drivers"

    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(100), nullable=False)
    phone         = db.Column(db.String(20), nullable=False)
    line_user_id  = db.Column(db.String(100))
    bind_status   = db.Column(db.String(20), default="未綁定")   # 未綁定 / 已綁定
    is_line_bound = db.Column(db.Boolean, default=False, nullable=False)
    bound_at      = db.Column(db.DateTime, nullable=True)
