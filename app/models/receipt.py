from datetime import datetime
from app import db

RECEIPT_TYPES = {
    "deposit": "訂金",
    "balance": "尾款",
    "refund":  "退款",
}

RECEIPT_TYPE_PREFIX = {
    "deposit": "DR",
    "balance": "PR",
    "refund":  "RR",
}


class Receipt(db.Model):
    __tablename__ = "receipts"

    id          = db.Column(db.Integer, primary_key=True)
    receipt_no  = db.Column(db.String(30), unique=True, nullable=False)
    receipt_type = db.Column(db.String(20), nullable=False)   # deposit / balance / refund
    order_id    = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    payment_id  = db.Column(db.Integer, db.ForeignKey("payments.id"), nullable=True)
    amount      = db.Column(db.Integer, nullable=False)
    issued_by   = db.Column(db.String(100), nullable=True)
    issued_at   = db.Column(db.DateTime, default=datetime.utcnow)
    status      = db.Column(db.String(20), default="active")  # active / void
    void_reason = db.Column(db.Text, nullable=True)
    void_by     = db.Column(db.String(100), nullable=True)
    void_at     = db.Column(db.DateTime, nullable=True)

    order   = db.relationship("Order",   backref="receipts",  lazy=True)
    payment = db.relationship("Payment", backref="receipts",  lazy=True)

    @property
    def type_label(self):
        return RECEIPT_TYPES.get(self.receipt_type, self.receipt_type)
