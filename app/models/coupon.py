from datetime import datetime, date
from app import db

DISCOUNT_TYPES = {
    "fixed":      "固定金額",
    "percentage": "百分比",
}


class Coupon(db.Model):
    __tablename__ = "coupons"

    id             = db.Column(db.Integer, primary_key=True)
    code           = db.Column(db.String(30), unique=True, nullable=False)
    name           = db.Column(db.String(100), nullable=False)
    discount_type  = db.Column(db.String(20), nullable=False)   # fixed / percentage
    discount_value = db.Column(db.Integer, nullable=False)       # NT$ or %
    start_date     = db.Column(db.Date, nullable=True)
    end_date       = db.Column(db.Date, nullable=True)
    max_uses       = db.Column(db.Integer, nullable=True)        # None = 不限
    use_count      = db.Column(db.Integer, nullable=False, default=0)
    is_active      = db.Column(db.Boolean, nullable=False, default=True)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def discount_label(self):
        if self.discount_type == "fixed":
            return f"NT${self.discount_value:,}"
        return f"{self.discount_value}%"

    @property
    def is_valid_now(self):
        today = date.today()
        if not self.is_active:
            return False
        if self.start_date and today < self.start_date:
            return False
        if self.end_date and today > self.end_date:
            return False
        if self.max_uses is not None and self.use_count >= self.max_uses:
            return False
        return True

    def calc_discount(self, total_amount: int) -> int:
        """計算折扣金額（不超過總金額）。"""
        if self.discount_type == "fixed":
            return min(self.discount_value, total_amount)
        pct = max(0, min(100, self.discount_value))
        return round(total_amount * pct / 100)
