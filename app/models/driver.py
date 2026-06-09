from app import db

class Driver(db.Model):
    __tablename__ = "drivers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    line_user_id = db.Column(db.String(100))
    bind_status = db.Column(db.String(20), default="未綁定")
