from datetime import datetime
from app import db


class Concert(db.Model):
    __tablename__ = "concerts"

    id          = db.Column(db.Integer, primary_key=True)
    artist      = db.Column(db.String(100), nullable=False)
    name        = db.Column(db.String(200), nullable=False)
    concert_date = db.Column(db.Date, nullable=True)
    city        = db.Column(db.String(50), nullable=True)
    venue       = db.Column(db.String(200), nullable=True)
    status      = db.Column(db.String(20), nullable=False, default="評估中")
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 爬蟲中心新增欄位（不修改既有欄位）
    crawler_hash      = db.Column(db.String(64),  nullable=True, unique=True, index=True)
    scheduler_enabled = db.Column(db.Boolean,     nullable=True, default=False)
    last_success_at   = db.Column(db.DateTime,    nullable=True)
    source_url        = db.Column(db.String(500), nullable=True)
    source_type       = db.Column(db.String(50),  nullable=True)
    source_urls       = db.Column(db.Text,        nullable=True)

    metrics      = db.relationship("ConcertMetrics",      back_populates="concert", uselist=False, cascade="all, delete-orphan")
    opportunities = db.relationship("ConcertOpportunity", back_populates="concert", cascade="all, delete-orphan")
    event_groups  = db.relationship("EventGroup",         back_populates="concert", cascade="all, delete-orphan")


class ConcertMetrics(db.Model):
    __tablename__ = "concert_metrics"

    id              = db.Column(db.Integer, primary_key=True)
    concert_id      = db.Column(db.Integer, db.ForeignKey("concerts.id", ondelete="CASCADE"), nullable=False, unique=True)
    popularity_score = db.Column(db.Float, nullable=True)
    opportunity_score = db.Column(db.Float, nullable=True)
    est_passengers  = db.Column(db.Integer, nullable=True)
    est_revenue     = db.Column(db.Integer, nullable=True)
    notes           = db.Column(db.Text, nullable=True)
    updated_at      = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    concert = db.relationship("Concert", back_populates="metrics")


class ConcertOpportunity(db.Model):
    __tablename__ = "concert_opportunities"

    id          = db.Column(db.Integer, primary_key=True)
    concert_id  = db.Column(db.Integer, db.ForeignKey("concerts.id", ondelete="CASCADE"), nullable=False)
    category    = db.Column(db.String(50), nullable=True)
    description = db.Column(db.Text, nullable=True)
    priority    = db.Column(db.String(20), default="中")
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    concert = db.relationship("Concert", back_populates="opportunities")


class EventGroup(db.Model):
    __tablename__ = "event_groups"

    id          = db.Column(db.Integer, primary_key=True)
    concert_id  = db.Column(db.Integer, db.ForeignKey("concerts.id", ondelete="CASCADE"), nullable=False)
    group_name  = db.Column(db.String(200), nullable=False)
    departure_date = db.Column(db.Date, nullable=True)
    vehicle_type   = db.Column(db.String(50), default="minibus")
    seat_limit     = db.Column(db.Integer, default=8)
    price_per_person = db.Column(db.Integer, default=2000)
    status      = db.Column(db.String(20), default="草稿")
    notes       = db.Column(db.Text, nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    concert = db.relationship("Concert", back_populates="event_groups")
