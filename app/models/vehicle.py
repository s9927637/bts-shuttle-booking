from app import db


class Vehicle(db.Model):
    __tablename__ = "vehicles"

    id           = db.Column(db.Integer, primary_key=True)
    name         = db.Column(db.String(100), nullable=True)   # 車輛名稱，例：九座商旅車
    plate_number = db.Column(db.String(50),  nullable=False)
    vehicle_type = db.Column(db.String(100), nullable=True)   # 車型，例：Volkswagen Caravelle
    seat_limit   = db.Column(db.Integer, default=8)
    driver_id    = db.Column(db.Integer, db.ForeignKey('drivers.id', ondelete='SET NULL'), nullable=True)

    # 保留舊欄位（向前相容，不刪除既有資料）
    driver_name  = db.Column(db.String(100), nullable=True)
    driver_phone = db.Column(db.String(20),  nullable=True)

    # 關聯：vehicle.driver → Driver 物件
    driver = db.relationship(
        'Driver',
        backref=db.backref('vehicles', lazy='select'),
        foreign_keys=[driver_id],
    )

    @property
    def display_name(self):
        return self.name or self.driver_name or f"車輛 {self.plate_number}"

    @property
    def display_driver_name(self):
        if self.driver:
            return self.driver.name
        return self.driver_name or "—"
