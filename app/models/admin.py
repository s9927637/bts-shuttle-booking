from datetime import datetime
from app import db

class Admin(db.Model):
    __tablename__ = "admins"

    id           = db.Column(db.Integer, primary_key=True)
    username     = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(100), nullable=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
