from datetime import datetime
from app import db

AUDIT_ACTIONS = {
    "payment_confirmed":    "確認付款",
    "receipt_issued":       "開立收據",
    "receipt_downloaded":   "下載收據",
    "receipt_resent":       "重新寄送收據",
    "receipt_voided":       "作廢收據",
    "order_modified":       "修改訂單",
    "order_cancelled":      "取消訂單",
}


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id          = db.Column(db.Integer, primary_key=True)
    admin_id    = db.Column(db.Integer, nullable=True)
    admin_name  = db.Column(db.String(100), nullable=True)
    action      = db.Column(db.String(60), nullable=False)
    target_type = db.Column(db.String(30), nullable=True)   # receipt / payment / order
    target_id   = db.Column(db.Integer, nullable=True)
    detail      = db.Column(db.Text, nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def action_label(self):
        return AUDIT_ACTIONS.get(self.action, self.action)
