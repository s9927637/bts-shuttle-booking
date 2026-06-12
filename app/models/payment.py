from datetime import datetime
from app import db

# payment_source 可選值：
#   bank_transfer_report  - 使用者提交匯款回報
#   admin_confirmed       - 後台管理員直接確認
#   legacy_customer       - 平台建立前舊客戶補單
#   cash                  - 現金付款

PAYMENT_SOURCES = {
    "bank_transfer_report": "匯款回報",
    "admin_confirmed":      "後台確認",
    "legacy_customer":      "舊客戶補單",
    "cash":                 "現金付款",
}

class Payment(db.Model):
    __tablename__ = "payments"

    id             = db.Column(db.Integer, primary_key=True)
    order_id       = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    payer_name     = db.Column(db.String(100))
    bank_last5     = db.Column(db.String(5))
    status         = db.Column(db.String(20), default="待確認")
    payment_source = db.Column(db.String(30), nullable=False, default="bank_transfer_report")
    amount         = db.Column(db.Integer, nullable=True)
    confirmed_at   = db.Column(db.DateTime, nullable=True)
    confirmed_by   = db.Column(db.String(100), nullable=True)
    note           = db.Column(db.Text, nullable=True)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
