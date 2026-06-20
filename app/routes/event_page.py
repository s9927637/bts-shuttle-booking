"""
活動模板系統 Blueprint

後台：/admin/event-pages/*
前台：/events/<slug>
"""
import re
from datetime import datetime

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, session, url_for

from app import db
from app.models.event_page import EventPage
from app.models.concert import Concert, EventGroup

event_page_bp = Blueprint("event_page", __name__)

# ── 藝人 slug 對照表 ─────────────────────────────────────────────────────────
_ARTIST_SLUG = {
    "BTS": "bts", "防彈少年團": "bts",
    "BLACKPINK": "blackpink", "블랙핑크": "blackpink",
    "TWICE": "twice", "트와이스": "twice",
    "aespa": "aespa", "에스파": "aespa",
    "IVE": "ive", "아이브": "ive",
    "SEVENTEEN": "seventeen", "세븐틴": "seventeen",
    "藤井風": "fujii-kaze",
    "Mr.Children": "mr-children", "Mr.children": "mr-children",
    "RADWIMPS": "radwimps",
    "ONE OK ROCK": "one-ok-rock",
    "LE SSERAFIM": "le-sserafim",
    "NewJeans": "newjeans",
    "stayc": "stayc", "STAYC": "stayc",
    "EXO": "exo", "NCT": "nct", "NCT 127": "nct-127",
    "SuperM": "superm", "SHINee": "shinee",
    "GOT7": "got7", "2PM": "2pm",
}

# ── 城市 slug 對照表 ─────────────────────────────────────────────────────────
_CITY_SLUG = {
    "高雄": "kaohsiung", "台北": "taipei", "臺北": "taipei",
    "台中": "taichung", "臺中": "taichung",
    "台南": "tainan",   "臺南": "tainan",
    "新北": "new-taipei", "桃園": "taoyuan", "新竹": "hsinchu",
    "嘉義": "chiayi",   "屏東": "pingtung", "花蓮": "hualien",
    "宜蘭": "yilan",    "台東": "taitung",
}


def _make_slug(artist_name: str, departure_city: str = "") -> str:
    """
    從藝人名稱 + 出發城市產生 URL-safe slug。
    例：'BTS', '高雄' → 'bts-kaohsiung'
    """
    # 藝人 slug：先查對照表，再 fallback 到 regex
    artist_part = _ARTIST_SLUG.get(artist_name.strip()) or re.sub(r"[^a-z0-9]+", "-", artist_name.strip().lower()).strip("-")

    # 城市轉 slug
    city_part = _CITY_SLUG.get(departure_city.strip(), "")
    if not city_part and departure_city:
        city_part = re.sub(r"[^a-z0-9]+", "-", departure_city.strip().lower()).strip("-")

    base = f"{artist_part}-{city_part}" if city_part else artist_part
    base = re.sub(r"-{2,}", "-", base)   # 合併多餘連字號

    # 處理重複：加尾碼
    slug = base
    n = 2
    while EventPage.query.filter_by(slug=slug).first():
        slug = f"{base}-{n}"
        n += 1
    return slug


def _require_admin():
    if not session.get("admin_id"):
        return redirect("/admin/login")
    return None


# ── 後台：活動列表 ──────────────────────────────────────────────────────────

@event_page_bp.route("/admin/event-pages/")
@event_page_bp.route("/admin/event-pages")
def ep_list():
    guard = _require_admin()
    if guard:
        return guard

    q = request.args.get("q", "").strip()
    query = EventPage.query.filter(EventPage.deleted_at.is_(None)).order_by(EventPage.created_at.desc())
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(EventPage.title.ilike(like), EventPage.artist_name.ilike(like))
        )
    pages = query.all()
    return render_template("admin/event_pages/list.html", pages=pages, q=q)


# ── 後台：建立活動（GET 顯示表單 / POST 送出）──────────────────────────────

@event_page_bp.route("/admin/event-pages/create", methods=["GET", "POST"])
def ep_create():
    guard = _require_admin()
    if guard:
        return guard

    concerts    = Concert.query.order_by(Concert.concert_date.asc()).all()
    event_groups = EventGroup.query.order_by(EventGroup.created_at.desc()).all()

    if request.method == "GET":
        return render_template("admin/event_pages/form.html",
                               mode="create", page=None,
                               concerts=concerts, event_groups=event_groups)

    # POST
    artist_name   = request.form.get("artist_name", "").strip()
    event_name    = request.form.get("event_name",  "").strip()
    departure_city = request.form.get("departure_city", "").strip()

    if not artist_name or not event_name:
        flash("藝人名稱與活動名稱為必填。", "error")
        return render_template("admin/event_pages/form.html",
                               mode="create", page=None,
                               concerts=concerts, event_groups=event_groups)

    title = request.form.get("title", "").strip() or f"{artist_name} {departure_city}演唱會包車"
    slug  = _make_slug(artist_name, departure_city)

    ep = EventPage(
        title=title,
        slug=slug,
        artist_name=artist_name,
        event_name=event_name,
        event_date=request.form.get("event_date", "").strip() or None,
        departure_city=departure_city or None,
        price=int(request.form.get("price", 2000) or 2000),
        deposit=int(request.form.get("deposit", 300) or 300),
        cover_image=request.form.get("cover_image", "").strip() or None,
        status=request.form.get("status", "草稿"),
        description=request.form.get("description", "").strip() or None,
        faq_content=request.form.get("faq_content", "").strip() or None,
        terms_content=request.form.get("terms_content", "").strip() or None,
        concert_id=int(request.form.get("concert_id") or 0) or None,
        event_group_id=int(request.form.get("event_group_id") or 0) or None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.session.add(ep)
    db.session.commit()
    flash(f"已建立活動「{title}」，網址：/events/{slug}", "success")
    return redirect(url_for("event_page.ep_list"))


# ── 後台：編輯活動 ──────────────────────────────────────────────────────────

@event_page_bp.route("/admin/event-pages/<int:ep_id>/edit", methods=["GET", "POST"])
def ep_edit(ep_id):
    guard = _require_admin()
    if guard:
        return guard

    ep = EventPage.query.get_or_404(ep_id)
    concerts     = Concert.query.order_by(Concert.concert_date.asc()).all()
    event_groups = EventGroup.query.order_by(EventGroup.created_at.desc()).all()

    if request.method == "GET":
        return render_template("admin/event_pages/form.html",
                               mode="edit", page=ep,
                               concerts=concerts, event_groups=event_groups)

    # POST
    ep.title        = request.form.get("title", ep.title).strip()
    ep.artist_name  = request.form.get("artist_name", ep.artist_name).strip()
    ep.event_name   = request.form.get("event_name", ep.event_name).strip()
    ep.event_date   = request.form.get("event_date", "").strip() or None
    ep.departure_city = request.form.get("departure_city", "").strip() or None
    ep.price        = int(request.form.get("price", ep.price or 2000) or 2000)
    ep.deposit      = int(request.form.get("deposit", ep.deposit or 300) or 300)
    ep.cover_image  = request.form.get("cover_image", "").strip() or None
    ep.status       = request.form.get("status", ep.status)
    ep.description  = request.form.get("description", "").strip() or None
    ep.faq_content  = request.form.get("faq_content", "").strip() or None
    ep.terms_content = request.form.get("terms_content", "").strip() or None
    ep.concert_id   = int(request.form.get("concert_id") or 0) or None
    ep.event_group_id = int(request.form.get("event_group_id") or 0) or None
    ep.updated_at   = datetime.utcnow()
    db.session.commit()
    flash(f"已更新活動「{ep.title}」。", "success")
    return redirect(url_for("event_page.ep_list"))


# ── 後台：軟刪除 ────────────────────────────────────────────────────────────

@event_page_bp.route("/admin/event-pages/<int:ep_id>/delete", methods=["POST"])
def ep_delete(ep_id):
    guard = _require_admin()
    if guard:
        return guard

    ep = EventPage.query.get_or_404(ep_id)
    ep.deleted_at = datetime.utcnow()
    db.session.commit()
    flash(f"已刪除活動「{ep.title}」。", "success")
    return redirect(url_for("event_page.ep_list"))


# ── 前台：活動頁 /events/<slug> ─────────────────────────────────────────────

@event_page_bp.route("/events/<slug>")
def event_show(slug):
    ep = EventPage.query.filter_by(slug=slug).filter(EventPage.deleted_at.is_(None)).first()
    if not ep:
        abort(404)
    if ep.status != "已發布":
        if not session.get("admin_id"):
            abort(404)
    # 計頁數（僅已發布的前台訪問，管理員預覽不計）
    if ep.status == "已發布" and not session.get("admin_id"):
        from app.services.event_metrics_service import increment_page_views
        increment_page_views(ep.id)
    return render_template("passenger/event_template.html", ep=ep)


# ── 後台：活動統計頁 /admin/events/statistics ────────────────────────────────

@event_page_bp.route("/admin/events/statistics")
def event_statistics():
    guard = _require_admin()
    if guard:
        return guard

    from app.models.event_metrics import EventMetrics
    from app.services.event_metrics_service import backfill_event_metrics

    event_pages = (
        EventPage.query
        .filter(EventPage.deleted_at.is_(None))
        .order_by(EventPage.created_at.desc())
        .all()
    )

    # 確保所有活動都有 metrics 列
    ep_ids_with_metrics = {m.event_page_id for m in EventMetrics.query.all()}
    needs_backfill = any(ep.id not in ep_ids_with_metrics for ep in event_pages)
    if needs_backfill:
        backfill_event_metrics()

    # 重新查詢（backfill 後 metrics 可能剛建立）
    stats = []
    for ep in event_pages:
        m = ep.metrics  # relationship backref
        stats.append({"ep": ep, "m": m})

    return render_template("admin/event_pages/statistics.html", stats=stats)


# ── 後台：活動詳細頁 /admin/events/<id> ──────────────────────────────────────

@event_page_bp.route("/admin/events/<int:ep_id>")
def event_detail(ep_id):
    guard = _require_admin()
    if guard:
        return guard

    from app.models.order import Order
    from app.models.event_metrics import EventMetrics
    from app.services.event_metrics_service import refresh_metrics

    ep = EventPage.query.get_or_404(ep_id)
    orders = ep.orders.order_by(Order.created_at.desc()).all()

    # 確保 metrics 存在並為最新
    m = ep.metrics
    if m is None:
        refresh_metrics(ep.id)
        db.session.commit()
        m = ep.metrics

    return render_template(
        "admin/event_pages/detail.html",
        ep=ep,
        orders=orders,
        m=m,
    )


# ── API：活動訂單列表 GET /api/events/<id>/orders ────────────────────────────

@event_page_bp.route("/api/events/<int:ep_id>/orders")
def api_event_orders(ep_id):
    if not session.get("admin_id"):
        return jsonify({"error": "未登入"}), 401

    from app.models.order import Order

    ep = EventPage.query.get_or_404(ep_id)
    orders = ep.orders.order_by(Order.created_at.desc()).all()
    return jsonify({
        "event_id":    ep.id,
        "event_title": ep.title,
        "orders": [
            {
                "id":             o.id,
                "order_no":       o.order_no,
                "contact_name":   o.contact_name,
                "phone":          o.phone,
                "departure_date": o.departure_date,
                "passenger_count": o.passenger_count,
                "total_amount":   o.total_amount,
                "deposit_amount": o.deposit_amount,
                "payment_status": o.payment_status,
                "created_at":     o.created_at.isoformat() if o.created_at else None,
            }
            for o in orders
        ],
    })


# ── API：單一活動統計 GET /api/events/<id>/statistics ───────────────────────

@event_page_bp.route("/api/events/<int:ep_id>/statistics")
def api_event_statistics(ep_id):
    if not session.get("admin_id"):
        return jsonify({"error": "未登入"}), 401

    from app.models.event_metrics import EventMetrics
    from app.services.event_metrics_service import refresh_metrics

    ep = EventPage.query.get_or_404(ep_id)
    m  = ep.metrics
    if m is None:
        refresh_metrics(ep.id)
        db.session.commit()
        m = ep.metrics

    return jsonify({
        "event_id":       ep.id,
        "event_title":    ep.title,
        "artist_name":    ep.artist_name,
        "bookings":       m.booking_count   if m else 0,
        "paid":           m.paid_count      if m else 0,
        "unpaid":         m.unpaid_count    if m else 0,
        "cancelled":      m.cancelled_count if m else 0,
        "passengers":     m.passenger_count if m else 0,
        "deposit_total":  m.deposit_amount  if m else 0,
        "revenue":        m.revenue_amount  if m else 0,
        "completion_rate": float(m.completion_rate) if m else 0,
        "page_views":     m.page_views      if m else 0,
    })


# ── API：全部活動統計 GET /api/events/statistics ─────────────────────────────

@event_page_bp.route("/api/events/statistics")
def api_events_statistics_all():
    if not session.get("admin_id"):
        return jsonify({"error": "未登入"}), 401

    from app.models.event_metrics import EventMetrics

    event_pages = (
        EventPage.query
        .filter(EventPage.deleted_at.is_(None))
        .order_by(EventPage.created_at.desc())
        .all()
    )

    result = []
    for ep in event_pages:
        m = ep.metrics
        result.append({
            "event_id":       ep.id,
            "event_title":    ep.title,
            "artist_name":    ep.artist_name,
            "slug":           ep.slug,
            "bookings":       m.booking_count   if m else 0,
            "paid":           m.paid_count      if m else 0,
            "passengers":     m.passenger_count if m else 0,
            "revenue":        m.revenue_amount  if m else 0,
            "completion_rate": float(m.completion_rate) if m else 0,
            "page_views":     m.page_views      if m else 0,
        })

    return jsonify({"events": result, "total": len(result)})
