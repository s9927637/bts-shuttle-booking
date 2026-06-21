"""
passenger_service — 乘客管理中心業務邏輯。

原則：
- 只讀取 orders（不修改），把統計快取到 passenger_profiles
- BTS 舊訂單、新活動訂單均納入乘客視角
- sync_passenger(phone) 可隨時重跑，冪等操作
"""
from __future__ import annotations
from datetime import datetime, date
from sqlalchemy import func
from app import db
from app.models.order import Order
from app.models.passenger_profile import PassengerProfile, PassengerTag


# ── 同步 ──────────────────────────────────────────────────────────────────────

def sync_passenger(phone: str) -> PassengerProfile:
    """從 orders 計算統計並 UPSERT passenger_profile。"""
    orders = Order.query.filter_by(phone=phone).all()
    if not orders:
        return None

    # 基本資料：取最新訂單
    latest = max(orders, key=lambda o: o.created_at or datetime(2000, 1, 1))
    name   = latest.contact_name
    lid    = latest.line_user_id
    dname  = latest.display_name

    # 統計
    total_orders = len(orders)
    event_ids    = {o.event_page_id for o in orders if o.event_page_id}
    # BTS 訂單（event_page_id=None）算一個活動
    has_bts      = any(o.event_page_id is None for o in orders)
    total_events = len(event_ids) + (1 if has_bts else 0)
    total_spent  = sum(o.total_amount or 0 for o in orders)
    last_order_at= max(
        (o.created_at for o in orders if o.created_at),
        default=None
    )

    profile = PassengerProfile.query.filter_by(phone=phone).first()
    if profile is None:
        profile = PassengerProfile(phone=phone, created_at=datetime.utcnow())
        db.session.add(profile)

    profile.name          = name
    profile.line_user_id  = lid
    profile.display_name  = dname
    profile.total_orders  = total_orders
    profile.total_events  = total_events
    profile.total_spent   = total_spent
    profile.last_order_at = last_order_at
    profile.updated_at    = datetime.utcnow()

    return profile


def sync_all_passengers() -> dict:
    """同步所有有訂單的乘客，回傳統計。"""
    phones = [
        r[0] for r in
        db.session.query(func.distinct(Order.phone)).all()
    ]
    created = updated = 0
    for phone in phones:
        existed = PassengerProfile.query.filter_by(phone=phone).first()
        sync_passenger(phone)
        if existed:
            updated += 1
        else:
            created += 1
    db.session.commit()
    return {"synced": len(phones), "created": created, "updated": updated}


# ── 查詢 ──────────────────────────────────────────────────────────────────────

def get_passenger_list(
    q: str = "",
    tag: str = "",
    page: int = 1,
    per_page: int = 20,
) -> dict:
    query = PassengerProfile.query

    if q:
        query = query.filter(
            db.or_(
                PassengerProfile.name.ilike(f"%{q}%"),
                PassengerProfile.phone.ilike(f"%{q}%"),
            )
        )
    if tag:
        query = query.join(PassengerTag).filter(PassengerTag.tag_name == tag)

    total = query.count()
    pages = max(1, (total + per_page - 1) // per_page)
    page  = min(page, pages)

    items = (
        query
        .order_by(PassengerProfile.last_order_at.desc().nullslast())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return {"items": items, "total": total, "page": page, "pages": pages}


def get_passenger_detail(passenger_id: int) -> dict:
    profile = PassengerProfile.query.get_or_404(passenger_id)
    orders  = Order.query.filter_by(phone=profile.phone).order_by(Order.created_at.desc()).all()

    # 歷史活動（不重複）
    from app.models.event_page import EventPage
    ep_ids = {o.event_page_id for o in orders if o.event_page_id}
    eps    = {ep.id: ep for ep in EventPage.query.filter(EventPage.id.in_(ep_ids)).all()} if ep_ids else {}
    has_bts = any(o.event_page_id is None for o in orders)

    events_history = []
    if has_bts:
        bts_count = sum(1 for o in orders if o.event_page_id is None)
        events_history.append({"title": "BTS 高雄演唱會", "artist": "BTS", "order_count": bts_count, "event_page": None})
    for eid, ep in eps.items():
        count = sum(1 for o in orders if o.event_page_id == eid)
        events_history.append({"title": ep.title, "artist": ep.artist_name, "order_count": count, "event_page": ep})

    # 付款紀錄
    from app.models.payment import Payment
    order_ids = [o.id for o in orders]
    payments  = Payment.query.filter(Payment.order_id.in_(order_ids)).order_by(Payment.created_at.desc()).all() if order_ids else []

    # 通知紀錄
    from app.models.notification import Notification
    notifications = Notification.query.filter(Notification.order_id.in_(order_ids)).order_by(Notification.created_at.desc()).all() if order_ids else []

    return {
        "profile":       profile,
        "orders":        orders,
        "events_history":events_history,
        "payments":      payments,
        "notifications": notifications,
        "predefined_tags": ["VIP", "高回購", "未付款", "黑名單", "高價值客戶", "常客", "新客"],
    }


# ── 統計 ──────────────────────────────────────────────────────────────────────

def get_passenger_statistics() -> dict:
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total        = PassengerProfile.query.count()
    vip_count    = (
        db.session.query(func.count(func.distinct(PassengerTag.passenger_id)))
        .filter(PassengerTag.tag_name == "VIP")
        .scalar() or 0
    )
    repurchase   = PassengerProfile.query.filter(PassengerProfile.total_orders >= 2).count()
    new_this_month = PassengerProfile.query.filter(
        PassengerProfile.created_at >= month_start
    ).count()

    return {
        "total":           total,
        "vip_count":       vip_count,
        "repurchase":      repurchase,
        "new_this_month":  new_this_month,
    }


# ── 標籤 ──────────────────────────────────────────────────────────────────────

def add_tag(passenger_id: int, tag_name: str) -> tuple[bool, str]:
    tag_name = tag_name.strip()
    if not tag_name:
        return False, "標籤名稱不可為空"
    existing = PassengerTag.query.filter_by(
        passenger_id=passenger_id, tag_name=tag_name
    ).first()
    if existing:
        return False, "標籤已存在"
    tag = PassengerTag(passenger_id=passenger_id, tag_name=tag_name)
    db.session.add(tag)
    return True, "OK"


def remove_tag(passenger_id: int, tag_name: str) -> tuple[bool, str]:
    tag = PassengerTag.query.filter_by(
        passenger_id=passenger_id, tag_name=tag_name
    ).first()
    if not tag:
        return False, "標籤不存在"
    db.session.delete(tag)
    return True, "OK"
