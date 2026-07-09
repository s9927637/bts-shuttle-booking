"""
活動模板系統 Blueprint

後台：/admin/event-pages/*
前台：/events/<slug>
"""
import re
from datetime import datetime

from flask import Blueprint, abort, flash, g, jsonify, redirect, render_template, request, session, url_for

from app import db, csrf
from app.models.event_page import EventPage
from app.models.event_hotspot import EventHotspot
from app.models.concert import Concert, EventGroup

event_page_bp = Blueprint("event_page", __name__)


# ══════════════════════════════════════════════════════════════════════════════
# Current Event Context
#
# 前台 /events/<slug>/* 底下所有路由（Landing／Booking／Orders／Remittance／
# Announcement／FAQ）共用同一份 EventPage 查詢，統一在這裡解析一次，存進
# g.current_event。各路由不得再自行 `EventPage.query.filter_by(slug=slug)`，
# 一律讀 g.current_event。未發布活動僅管理員（session admin_id）可預覽。
#
# 透過 app 層級的 context_processor（見 app/__init__.py）自動注入
# `current_event` 供所有 template 使用，不需要每個 render_template() 手動傳入。
# ══════════════════════════════════════════════════════════════════════════════

@event_page_bp.before_request
def _load_current_event():
    slug = (request.view_args or {}).get("slug")
    if not slug:
        g.current_event = None
        return
    ep = EventPage.query.filter_by(slug=slug).filter(EventPage.deleted_at.is_(None)).first()
    if not ep or (ep.status != "已發布" and not session.get("admin_id")):
        g.current_event = None
        return
    g.current_event = ep

def _logo_hotspot_form_kwargs():
    """從 request.form 解析 Logo Display Mode + 三裝置 Logo Hotspot 座標"""
    mode = request.form.get("logo_display_mode", "landing_hotspot").strip()
    if mode not in ("system", "landing_hotspot"):
        mode = "landing_hotspot"
    kwargs = {"logo_display_mode": mode}
    for device in ("desktop", "tablet", "mobile"):
        for axis in ("x", "y", "w", "h"):
            field = f"logo_hotspot_{device}_{axis}"
            raw = request.form.get(field, "").strip()
            try:
                kwargs[field] = float(raw) if raw else None
            except ValueError:
                kwargs[field] = None
    return kwargs


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

@event_page_bp.route("/admin/events")
@event_page_bp.route("/admin/events/")
def ep_list_alias():
    return redirect(url_for("event_page.ep_list"))


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

    def _parse_dt(field):
        v = request.form.get(field, "").strip()
        try:
            return datetime.fromisoformat(v) if v else None
        except ValueError:
            return None

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
        banner_image=request.form.get("banner_image", "").strip() or None,
        thumbnail_image=request.form.get("thumbnail_image", "").strip() or None,
        category=request.form.get("category", "concert") or "concert",
        venue=request.form.get("venue", "").strip() or None,
        booking_open_at=_parse_dt("booking_open_at"),
        booking_close_at=_parse_dt("booking_close_at"),
        status=request.form.get("status", "草稿"),
        description=request.form.get("description", "").strip() or None,
        faq_content=request.form.get("faq_content", "").strip() or None,
        terms_content=request.form.get("terms_content", "").strip() or None,
        theme_color=request.form.get("theme_color", "purple") or "purple",
        subtitle=request.form.get("subtitle", "").strip() or None,
        feat1_title=request.form.get("feat1_title", "").strip() or None,
        feat1_sub=request.form.get("feat1_sub", "").strip() or None,
        feat2_title=request.form.get("feat2_title", "").strip() or None,
        feat2_sub=request.form.get("feat2_sub", "").strip() or None,
        feat3_title=request.form.get("feat3_title", "").strip() or None,
        feat3_sub=request.form.get("feat3_sub", "").strip() or None,
        feat4_title=request.form.get("feat4_title", "").strip() or None,
        feat4_sub=request.form.get("feat4_sub", "").strip() or None,
        tour_name=request.form.get("tour_name", "").strip() or None,
        hero_image_desktop=request.form.get("hero_image_desktop", "").strip() or None,
        hero_image_tablet=request.form.get("hero_image_tablet", "").strip() or None,
        hero_image_mobile=request.form.get("hero_image_mobile", "").strip() or None,
        logo_text=request.form.get("logo_text", "").strip() or None,
        theme_navbar=request.form.get("theme_navbar", "auto").strip() or "auto",
        cta_enabled=bool(request.form.get("cta_enabled")),
        footer_enabled=bool(request.form.get("footer_enabled")),
        footer_text=request.form.get("footer_text", "").strip() or None,
        footer_privacy_url=request.form.get("footer_privacy_url", "").strip() or None,
        footer_terms_url=request.form.get("footer_terms_url", "").strip() or None,
        footer_contact_url=request.form.get("footer_contact_url", "").strip() or None,
        concert_id=int(request.form.get("concert_id") or 0) or None,
        event_group_id=int(request.form.get("event_group_id") or 0) or None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        **_logo_hotspot_form_kwargs(),
    )
    db.session.add(ep)
    db.session.commit()
    flash(f"✓ 已建立活動「{title}」，網址：/events/{slug}　← 現在可上傳 Hero 圖片", "success")
    return redirect(url_for("event_page.ep_edit", ep_id=ep.id))


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
        device = request.args.get("device", "desktop").strip()
        if device not in EventHotspot.DEVICES:
            device = "desktop"
        hotspots = ep.hotspots.filter_by(device=device).order_by(EventHotspot.sort_order).all()
        device_image = {
            "desktop": ep.landing_image_desktop,
            "tablet":  ep.landing_image_tablet,
            "mobile":  ep.landing_image_mobile,
        }[device]
        return render_template("admin/event_pages/form.html",
                               mode="edit", page=ep,
                               concerts=concerts, event_groups=event_groups,
                               device=device, device_image=device_image, hotspots=hotspots,
                               devices=EventHotspot.DEVICES, device_labels=EventHotspot.DEVICE_LABELS,
                               link_types=EventHotspot.LINK_TYPES,
                               link_type_labels=EventHotspot.LINK_TYPE_LABELS)

    # POST
    def _parse_dt_edit(field):
        v = request.form.get(field, "").strip()
        try:
            return datetime.fromisoformat(v) if v else None
        except ValueError:
            return None

    ep.title          = request.form.get("title", ep.title).strip()
    ep.artist_name    = request.form.get("artist_name", ep.artist_name).strip()
    ep.event_name     = request.form.get("event_name", ep.event_name).strip()
    ep.event_date     = request.form.get("event_date", "").strip() or None
    ep.departure_city = request.form.get("departure_city", "").strip() or None
    ep.price          = int(request.form.get("price", ep.price or 2000) or 2000)
    ep.deposit        = int(request.form.get("deposit", ep.deposit or 300) or 300)
    ep.cover_image    = request.form.get("cover_image", "").strip() or None
    ep.banner_image   = request.form.get("banner_image", "").strip() or None
    ep.thumbnail_image = request.form.get("thumbnail_image", "").strip() or None
    ep.category       = request.form.get("category", ep.category or "concert") or "concert"
    ep.venue          = request.form.get("venue", "").strip() or None
    ep.booking_open_at  = _parse_dt_edit("booking_open_at")
    ep.booking_close_at = _parse_dt_edit("booking_close_at")
    ep.status         = request.form.get("status", ep.status)
    ep.description    = request.form.get("description", "").strip() or None
    ep.faq_content    = request.form.get("faq_content", "").strip() or None
    ep.terms_content  = request.form.get("terms_content", "").strip() or None
    ep.theme_color    = request.form.get("theme_color", ep.theme_color or "purple") or "purple"
    ep.subtitle       = request.form.get("subtitle", "").strip() or None
    ep.feat1_title    = request.form.get("feat1_title", "").strip() or None
    ep.feat1_sub      = request.form.get("feat1_sub", "").strip() or None
    ep.feat2_title    = request.form.get("feat2_title", "").strip() or None
    ep.feat2_sub      = request.form.get("feat2_sub", "").strip() or None
    ep.feat3_title    = request.form.get("feat3_title", "").strip() or None
    ep.feat3_sub      = request.form.get("feat3_sub", "").strip() or None
    ep.feat4_title    = request.form.get("feat4_title", "").strip() or None
    ep.feat4_sub      = request.form.get("feat4_sub", "").strip() or None
    ep.tour_name           = request.form.get("tour_name", "").strip() or None
    ep.hero_image_desktop  = request.form.get("hero_image_desktop", "").strip() or None
    ep.hero_image_tablet   = request.form.get("hero_image_tablet", "").strip() or None
    ep.hero_image_mobile   = request.form.get("hero_image_mobile", "").strip() or None
    ep.logo_text  = request.form.get("logo_text", "").strip() or None
    # Phase 10: Theme System
    def _hex(key):
        v = request.form.get(key, "").strip()
        return v if v and v.startswith('#') and len(v) in (4, 7) else None
    ep.theme_primary_color   = _hex("theme_primary_color")
    ep.theme_secondary_color = _hex("theme_secondary_color")
    ep.theme_bg_color        = _hex("theme_bg_color")
    ep.theme_text_color      = _hex("theme_text_color")
    ep.theme_btn_color       = _hex("theme_btn_color")
    ep.theme_btn_text_color  = _hex("theme_btn_text_color")
    ep.theme_navbar          = request.form.get("theme_navbar", "auto").strip() or "auto"
    ep.cta_enabled    = bool(request.form.get("cta_enabled"))
    ep.footer_enabled = bool(request.form.get("footer_enabled"))
    ep.footer_text         = request.form.get("footer_text", "").strip() or None
    ep.footer_privacy_url  = request.form.get("footer_privacy_url", "").strip() or None
    ep.footer_terms_url    = request.form.get("footer_terms_url", "").strip() or None
    ep.footer_contact_url  = request.form.get("footer_contact_url", "").strip() or None
    ep.landing_published = bool(request.form.get("landing_published"))
    for field, value in _logo_hotspot_form_kwargs().items():
        setattr(ep, field, value)
    ep.concert_id     = int(request.form.get("concert_id") or 0) or None
    ep.event_group_id = int(request.form.get("event_group_id") or 0) or None
    ep.updated_at     = datetime.utcnow()
    db.session.commit()
    flash(f"✓ 已儲存「{ep.title}」", "success")
    return redirect(url_for("event_page.ep_edit", ep_id=ep.id))


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
    ep = g.current_event
    if not ep:
        abort(404)
    # 計頁數（僅已發布的前台訪問，管理員預覽不計）
    if ep.status == "已發布" and not session.get("admin_id"):
        from app.services.event_metrics_service import increment_page_views
        increment_page_views(ep.id)
    hotspots_by_device = {"desktop": [], "tablet": [], "mobile": []}
    if ep.has_image_landing:
        for device in EventHotspot.DEVICES:
            hotspots_by_device[device] = (
                ep.hotspots.filter_by(is_active=True, device=device)
                .order_by(EventHotspot.sort_order).all()
            )
    return render_template("passenger/event_template.html", ep=ep, hotspots_by_device=hotspots_by_device)


# ── 前台：活動公告 /events/<slug>/news ─────────────────────────────────────

@event_page_bp.route("/events/<slug>/news")
def event_news(slug):
    from app.models.announcement import Announcement
    ep = g.current_event
    if not ep:
        abort(404)
    page = request.args.get("page", 1, type=int)
    per_page = 10
    q = (Announcement.query
         .filter(
             Announcement.status == "已發布",
             db.or_(Announcement.event_page_id == ep.id, Announcement.event_page_id.is_(None))
         )
         .order_by(Announcement.is_pinned.desc(), Announcement.created_at.desc()))
    pagination = q.paginate(page=page, per_page=per_page, error_out=False)
    return render_template("passenger/event_news.html",
                           ep=ep, announcements=pagination.items,
                           pagination=pagination)


# ── 前台：活動 FAQ /events/<slug>/faq ───────────────────────────────────────

@event_page_bp.route("/events/<slug>/faq")
def event_faq(slug):
    from app.models.faq import Faq
    ep = g.current_event
    if not ep:
        abort(404)
    faqs = Faq.query.filter_by(event_page_id=ep.id, is_active=True).order_by(Faq.sort_order).all()
    return render_template("passenger/event_faq.html", ep=ep, faqs=faqs)


# ── 前台：活動預約 /events/<slug>/booking（redirect，帶 event_id）────────────

@event_page_bp.route("/events/<slug>/booking")
def event_booking(slug):
    ep = g.current_event
    if not ep:
        abort(404)
    from app.routes.passenger import _render_booking_page
    friend_code = request.args.get("friend_code", "").strip() or None
    return _render_booking_page(event_page=ep, friend_code=friend_code)


# ── 前台：活動查詢訂單 /events/<slug>/orders ────────────────────────────────

@event_page_bp.route("/events/<slug>/orders")
def event_orders(slug):
    ep = g.current_event
    if not ep:
        abort(404)
    from app.routes.passenger import _render_order_search_page
    return _render_order_search_page(event_page=ep)


# ── 前台：活動匯款回報 /events/<slug>/remittance ────────────────────────────

@event_page_bp.route("/events/<slug>/remittance")
def event_remittance(slug):
    ep = g.current_event
    if not ep:
        abort(404)
    from app.routes.passenger import _render_payment_report_page
    return _render_payment_report_page(event_page=ep)


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


# ══════════════════════════════════════════════════════════════════════════════
# Hero Image Upload API
# ══════════════════════════════════════════════════════════════════════════════

@event_page_bp.route("/api/events/<int:ep_id>/upload-hero", methods=["POST"])
@csrf.exempt
def api_upload_hero(ep_id):
    """上傳 Hero 圖片（desktop / tablet / mobile）"""
    if not session.get("admin_id"):
        return jsonify({"error": "未登入"}), 401

    ep = EventPage.query.get_or_404(ep_id)
    slot = request.form.get("slot", "").strip()  # desktop | tablet | mobile
    file = request.files.get("file")

    from app.services.upload_service import save_hero_image, allowed_file
    try:
        url = save_hero_image(file, ep_id, slot)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    # 更新 DB
    if slot == "desktop":
        ep.hero_image_desktop = url
    elif slot == "tablet":
        ep.hero_image_tablet = url
    elif slot == "mobile":
        ep.hero_image_mobile = url
    else:
        return jsonify({"error": "無效 slot"}), 400

    ep.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({"ok": True, "url": url, "slot": slot})


@event_page_bp.route("/api/events/<int:ep_id>/delete-hero", methods=["POST"])
@csrf.exempt
def api_delete_hero(ep_id):
    """刪除指定 slot Hero 圖片"""
    if not session.get("admin_id"):
        return jsonify({"error": "未登入"}), 401

    ep = EventPage.query.get_or_404(ep_id)
    data = request.get_json(silent=True) or {}
    slot = data.get("slot", "").strip()

    from app.services.upload_service import delete_hero_image
    if slot not in ("desktop", "tablet", "mobile"):
        return jsonify({"error": "無效 slot"}), 400

    delete_hero_image(ep_id, slot)

    if slot == "desktop":
        ep.hero_image_desktop = None
    elif slot == "tablet":
        ep.hero_image_tablet = None
    elif slot == "mobile":
        ep.hero_image_mobile = None

    ep.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"ok": True})


# ══════════════════════════════════════════════════════════════════════════════
# V1: Landing Image Upload API（圖片 Landing + Hotspot）
# ══════════════════════════════════════════════════════════════════════════════

@event_page_bp.route("/api/events/<int:ep_id>/upload-landing-image", methods=["POST"])
@csrf.exempt
def api_upload_landing_image(ep_id):
    """上傳 Landing 圖片（desktop / tablet / mobile）"""
    if not session.get("admin_id"):
        return jsonify({"error": "未登入"}), 401

    ep = EventPage.query.get_or_404(ep_id)
    slot = request.form.get("slot", "").strip()
    file = request.files.get("file")

    from app.services.upload_service import save_hero_image
    try:
        url = save_hero_image(file, ep_id, slot, prefix="landing")
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    if slot == "desktop":
        ep.landing_image_desktop = url
    elif slot == "tablet":
        ep.landing_image_tablet = url
    elif slot == "mobile":
        ep.landing_image_mobile = url
    else:
        return jsonify({"error": "無效 slot"}), 400

    ep.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"ok": True, "url": url, "slot": slot})


@event_page_bp.route("/api/events/<int:ep_id>/delete-landing-image", methods=["POST"])
@csrf.exempt
def api_delete_landing_image(ep_id):
    """刪除指定 slot Landing 圖片"""
    if not session.get("admin_id"):
        return jsonify({"error": "未登入"}), 401

    ep = EventPage.query.get_or_404(ep_id)
    data = request.get_json(silent=True) or {}
    slot = data.get("slot", "").strip()

    from app.services.upload_service import delete_hero_image
    if slot not in ("desktop", "tablet", "mobile"):
        return jsonify({"error": "無效 slot"}), 400

    delete_hero_image(ep_id, slot, prefix="landing")

    if slot == "desktop":
        ep.landing_image_desktop = None
    elif slot == "tablet":
        ep.landing_image_tablet = None
    elif slot == "mobile":
        ep.landing_image_mobile = None

    ep.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"ok": True})


# ══════════════════════════════════════════════════════════════════════════════
# V1: Hotspot CRUD API
# ══════════════════════════════════════════════════════════════════════════════

@event_page_bp.route("/api/events/<int:ep_id>/hotspots", methods=["GET", "POST"])
@csrf.exempt
def api_hotspots(ep_id):
    if not session.get("admin_id"):
        return jsonify({"error": "未登入"}), 401
    ep = EventPage.query.get_or_404(ep_id)

    if request.method == "GET":
        device = request.args.get("device", "").strip()
        q = ep.hotspots
        if device:
            if device not in EventHotspot.DEVICES:
                return jsonify({"error": "無效的 device"}), 400
            q = q.filter_by(device=device)
        hs_list = q.all()
        return jsonify({"hotspots": [
            {"id": h.id, "device": h.device, "label": h.label, "link_type": h.link_type, "custom_url": h.custom_url,
             "x_pct": h.x_pct, "y_pct": h.y_pct, "w_pct": h.w_pct, "h_pct": h.h_pct,
             "sort_order": h.sort_order, "is_active": h.is_active}
            for h in hs_list
        ]})

    data = request.get_json(silent=True) or {}
    link_type = data.get("link_type", "booking")
    if link_type not in EventHotspot.LINK_TYPES:
        return jsonify({"error": "無效的 link_type"}), 400
    device = data.get("device", "desktop")
    if device not in EventHotspot.DEVICES:
        return jsonify({"error": "無效的 device"}), 400
    max_order = (
        db.session.query(db.func.max(EventHotspot.sort_order))
        .filter_by(event_id=ep_id, device=device).scalar() or 0
    )
    hs = EventHotspot(
        event_id=ep_id,
        device=device,
        label=(data.get("label") or "").strip() or "熱點",
        link_type=link_type,
        custom_url=(data.get("custom_url") or "").strip() or None,
        x_pct=float(data.get("x_pct", 10)),
        y_pct=float(data.get("y_pct", 10)),
        w_pct=float(data.get("w_pct", 20)),
        h_pct=float(data.get("h_pct", 10)),
        sort_order=max_order + 1,
        is_active=True,
    )
    db.session.add(hs)
    db.session.commit()
    return jsonify({"ok": True, "id": hs.id})


@event_page_bp.route("/api/events/<int:ep_id>/hotspots/<int:hs_id>", methods=["PUT", "DELETE"])
@csrf.exempt
def api_hotspot_detail(ep_id, hs_id):
    if not session.get("admin_id"):
        return jsonify({"error": "未登入"}), 401
    hs = EventHotspot.query.get_or_404(hs_id)
    if hs.event_id != ep_id:
        abort(404)

    if request.method == "DELETE":
        db.session.delete(hs)
        db.session.commit()
        return jsonify({"ok": True})

    data = request.get_json(silent=True) or {}
    if "label" in data:
        hs.label = (data.get("label") or "").strip() or hs.label
    if "link_type" in data and data["link_type"] in EventHotspot.LINK_TYPES:
        hs.link_type = data["link_type"]
    if "custom_url" in data:
        hs.custom_url = (data.get("custom_url") or "").strip() or None
    for field in ("x_pct", "y_pct", "w_pct", "h_pct"):
        if field in data:
            setattr(hs, field, float(data[field]))
    if "is_active" in data:
        hs.is_active = bool(data["is_active"])
    hs.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"ok": True})


# ══════════════════════════════════════════════════════════════════════════════
# V1: Logo Hotspot（獨立於 Landing Hotspot，每裝置固定一個，不可新增/刪除）
# ══════════════════════════════════════════════════════════════════════════════

@event_page_bp.route("/api/events/<int:ep_id>/copy-logo-hotspot", methods=["POST"])
@csrf.exempt
def api_copy_logo_hotspot(ep_id):
    """把目前輸入中的 Logo Hotspot 座標（來源固定為 Desktop 編輯器）複製到指定裝置"""
    if not session.get("admin_id"):
        return jsonify({"error": "未登入"}), 401
    ep = EventPage.query.get_or_404(ep_id)

    data = request.get_json(silent=True) or {}
    targets = data.get("targets") or []
    targets = [t for t in targets if t in EventHotspot.DEVICES]
    if not targets:
        return jsonify({"error": "無效的目標裝置"}), 400

    try:
        x = float(data.get("x", 2))
        y = float(data.get("y", 2))
        w = float(data.get("w", 15))
        h = float(data.get("h", 6))
    except (TypeError, ValueError):
        return jsonify({"error": "座標格式錯誤"}), 400

    # 來源裝置（Desktop）本身也一併寫入，確保複製當下即生效，不需等待主表單儲存
    for device in set(targets) | {"desktop"}:
        setattr(ep, f"logo_hotspot_{device}_x", x)
        setattr(ep, f"logo_hotspot_{device}_y", y)
        setattr(ep, f"logo_hotspot_{device}_w", w)
        setattr(ep, f"logo_hotspot_{device}_h", h)
    ep.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"ok": True, "targets": targets})


@event_page_bp.route("/api/events/<int:ep_id>/logo-hotspot", methods=["PUT"])
@csrf.exempt
def api_update_logo_hotspot(ep_id):
    """單一裝置 Logo Hotspot 座標即時更新（Visual Editor 拖曳/縮放結束後自動儲存，僅影響當前裝置）"""
    if not session.get("admin_id"):
        return jsonify({"error": "未登入"}), 401
    ep = EventPage.query.get_or_404(ep_id)

    data = request.get_json(silent=True) or {}
    device = data.get("device")
    if device not in EventHotspot.DEVICES:
        return jsonify({"error": "無效的裝置"}), 400

    try:
        x = float(data.get("x", 2))
        y = float(data.get("y", 2))
        w = float(data.get("w", 15))
        h = float(data.get("h", 6))
    except (TypeError, ValueError):
        return jsonify({"error": "座標格式錯誤"}), 400

    setattr(ep, f"logo_hotspot_{device}_x", x)
    setattr(ep, f"logo_hotspot_{device}_y", y)
    setattr(ep, f"logo_hotspot_{device}_w", w)
    setattr(ep, f"logo_hotspot_{device}_h", h)
    ep.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"ok": True})


@event_page_bp.route("/api/events/<int:ep_id>/upload-logo", methods=["POST"])
@csrf.exempt
def api_upload_logo(ep_id):
    """上傳活動 Logo（PNG/SVG/WebP）"""
    if not session.get("admin_id"):
        return jsonify({"error": "未登入"}), 401
    ep = EventPage.query.get_or_404(ep_id)
    file = request.files.get("file")
    from app.services.upload_service import save_logo_image
    try:
        url = save_logo_image(file, ep_id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    ep.logo_image = url
    ep.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"ok": True, "url": url})


@event_page_bp.route("/api/events/<int:ep_id>/delete-logo", methods=["POST"])
@csrf.exempt
def api_delete_logo(ep_id):
    """刪除活動 Logo"""
    if not session.get("admin_id"):
        return jsonify({"error": "未登入"}), 401
    ep = EventPage.query.get_or_404(ep_id)
    from app.services.upload_service import delete_logo_image
    delete_logo_image(ep_id)
    ep.logo_image = None
    ep.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"ok": True})


# ══════════════════════════════════════════════════════════════════════════════
# Landing Page 已併入活動編輯頁（/admin/event-pages/<id>/edit 的「Landing Page」
# 區塊，原「Hero Media Manager」位置），不再獨立成頁。此路由僅為相容舊連結
# （例如既有書籤／外部連結）保留，導向新位置。
# ══════════════════════════════════════════════════════════════════════════════

@event_page_bp.route("/admin/event-pages/<int:ep_id>/landing", methods=["GET", "POST"])
def ep_landing(ep_id):
    guard = _require_admin()
    if guard:
        return guard
    device = request.args.get("device", "").strip()
    target = url_for("event_page.ep_edit", ep_id=ep_id)
    if device:
        target += f"?device={device}"
    return redirect(target)


# ── 後台：即時預覽（Desktop/Tablet/Mobile 切換）──────────────────────────────

@event_page_bp.route("/admin/events/<int:ep_id>/preview")
def ep_preview(ep_id):
    guard = _require_admin()
    if guard:
        return guard
    ep = EventPage.query.get_or_404(ep_id)
    return render_template("admin/event_pages/preview.html", ep=ep)


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 4  活動複製
# ══════════════════════════════════════════════════════════════════════════════

@event_page_bp.route("/admin/events/<int:ep_id>/clone", methods=["POST"])
def ep_clone(ep_id):
    guard = _require_admin()
    if guard:
        return guard

    src = EventPage.query.get_or_404(ep_id)

    new_title = f"{src.title} (副本)"
    base_slug  = f"{src.slug}-copy"
    new_slug   = base_slug
    n = 2
    while EventPage.query.filter_by(slug=new_slug).first():
        new_slug = f"{base_slug}-{n}"
        n += 1

    clone = EventPage(
        title=new_title,
        slug=new_slug,
        artist_name=src.artist_name,
        event_name=src.event_name,
        event_date=src.event_date,
        departure_city=src.departure_city,
        price=src.price,
        deposit=src.deposit,
        cover_image=src.cover_image,
        banner_image=src.banner_image,
        thumbnail_image=src.thumbnail_image,
        status="草稿",
        description=src.description,
        faq_content=src.faq_content,
        terms_content=src.terms_content,
        category=src.category,
        venue=src.venue,
        booking_open_at=src.booking_open_at,
        booking_close_at=src.booking_close_at,
        concert_id=src.concert_id,
        event_group_id=src.event_group_id,
        theme_color=src.theme_color,
        subtitle=src.subtitle,
        feat1_title=src.feat1_title,
        feat1_sub=src.feat1_sub,
        feat2_title=src.feat2_title,
        feat2_sub=src.feat2_sub,
        feat3_title=src.feat3_title,
        feat3_sub=src.feat3_sub,
        feat4_title=src.feat4_title,
        feat4_sub=src.feat4_sub,
        tour_name=src.tour_name,
        hero_image_desktop=src.hero_image_desktop,
        hero_image_tablet=src.hero_image_tablet,
        hero_image_mobile=src.hero_image_mobile,
        landing_html=src.landing_html,
        landing_css=src.landing_css,
        landing_js=src.landing_js,
        landing_image_desktop=src.landing_image_desktop,
        landing_image_tablet=src.landing_image_tablet,
        landing_image_mobile=src.landing_image_mobile,
        landing_published=False,   # 複製後預設下架，需重新確認後手動發布
        logo_display_mode=src.logo_display_mode,
        logo_hotspot_desktop_x=src.logo_hotspot_desktop_x,
        logo_hotspot_desktop_y=src.logo_hotspot_desktop_y,
        logo_hotspot_desktop_w=src.logo_hotspot_desktop_w,
        logo_hotspot_desktop_h=src.logo_hotspot_desktop_h,
        logo_hotspot_tablet_x=src.logo_hotspot_tablet_x,
        logo_hotspot_tablet_y=src.logo_hotspot_tablet_y,
        logo_hotspot_tablet_w=src.logo_hotspot_tablet_w,
        logo_hotspot_tablet_h=src.logo_hotspot_tablet_h,
        logo_hotspot_mobile_x=src.logo_hotspot_mobile_x,
        logo_hotspot_mobile_y=src.logo_hotspot_mobile_y,
        logo_hotspot_mobile_w=src.logo_hotspot_mobile_w,
        logo_hotspot_mobile_h=src.logo_hotspot_mobile_h,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.session.add(clone)
    db.session.flush()   # 取得 clone.id 供複製 Hotspot 使用

    for hs in src.hotspots.all():
        db.session.add(EventHotspot(
            event_id=clone.id,
            device=hs.device,
            label=hs.label,
            link_type=hs.link_type,
            custom_url=hs.custom_url,
            x_pct=hs.x_pct, y_pct=hs.y_pct, w_pct=hs.w_pct, h_pct=hs.h_pct,
            sort_order=hs.sort_order,
            is_active=hs.is_active,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ))

    db.session.commit()
    flash(f"已複製活動「{new_title}」，請修改後發布。", "success")
    return redirect(url_for("event_page.ep_edit", ep_id=clone.id))


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 5  公開活動列表  /events
# ══════════════════════════════════════════════════════════════════════════════

@event_page_bp.route("/events")
def events_list():
    category = request.args.get("category", "").strip()
    query = (
        EventPage.query
        .filter(EventPage.deleted_at.is_(None), EventPage.status == "已發布")
        .order_by(EventPage.event_date.asc(), EventPage.created_at.desc())
    )
    if category:
        query = query.filter(EventPage.category == category)

    events = query.all()
    categories = EventPage.CATEGORY_LABELS
    return render_template("passenger/events.html",
                           events=events,
                           categories=categories,
                           current_category=category)


# ══════════════════════════════════════════════════════════════════════════════
# BOOKING CONFIG API  /api/events/<ep_id>/booking-*
# ══════════════════════════════════════════════════════════════════════════════

from app.models.event_booking import EventBookingDate, EventPickupLocation, EventPriceRule, EventFormConfig as _EFC


# ── 搭車日期 ──────────────────────────────────────────────────────────────────

@event_page_bp.route("/api/events/<int:ep_id>/booking-dates", methods=["GET"])
def api_booking_dates_list(ep_id):
    ep = EventPage.query.get_or_404(ep_id)
    dates = EventBookingDate.query.filter_by(event_page_id=ep.id).order_by(EventBookingDate.sort_order).all()
    return jsonify([{
        "id": d.id, "date_value": d.date_value, "label": d.label,
        "sort_order": d.sort_order, "is_active": d.is_active, "capacity": d.capacity
    } for d in dates])


@event_page_bp.route("/api/events/<int:ep_id>/booking-dates", methods=["POST"])
def api_booking_date_create(ep_id):
    ep = EventPage.query.get_or_404(ep_id)
    data = request.get_json(force=True) or {}
    date_value = (data.get("date_value") or "").strip()
    if not date_value:
        return jsonify({"error": "date_value 必填"}), 400
    d = EventBookingDate(
        event_page_id=ep.id,
        date_value=date_value,
        label=(data.get("label") or "").strip() or None,
        sort_order=int(data.get("sort_order") or 0),
        is_active=bool(data.get("is_active", True)),
        capacity=int(data["capacity"]) if data.get("capacity") else None,
    )
    db.session.add(d)
    db.session.commit()
    return jsonify({"id": d.id, "date_value": d.date_value, "label": d.label}), 201


@event_page_bp.route("/api/events/<int:ep_id>/booking-dates/<int:date_id>", methods=["PUT"])
def api_booking_date_update(ep_id, date_id):
    d = EventBookingDate.query.filter_by(id=date_id, event_page_id=ep_id).first_or_404()
    data = request.get_json(force=True) or {}
    if "date_value" in data: d.date_value = data["date_value"].strip()
    if "label"      in data: d.label      = (data["label"] or "").strip() or None
    if "sort_order" in data: d.sort_order = int(data["sort_order"])
    if "is_active"  in data: d.is_active  = bool(data["is_active"])
    if "capacity"   in data: d.capacity   = int(data["capacity"]) if data["capacity"] else None
    db.session.commit()
    return jsonify({"ok": True})


@event_page_bp.route("/api/events/<int:ep_id>/booking-dates/<int:date_id>", methods=["DELETE"])
def api_booking_date_delete(ep_id, date_id):
    d = EventBookingDate.query.filter_by(id=date_id, event_page_id=ep_id).first_or_404()
    db.session.delete(d)
    db.session.commit()
    return jsonify({"ok": True})


# ── 上車地點 ──────────────────────────────────────────────────────────────────

@event_page_bp.route("/api/events/<int:ep_id>/pickup-locations", methods=["GET"])
def api_locations_list(ep_id):
    ep = EventPage.query.get_or_404(ep_id)
    locs = EventPickupLocation.query.filter_by(event_page_id=ep.id).order_by(EventPickupLocation.sort_order).all()
    return jsonify([{
        "id": l.id, "name": l.name, "address": l.address,
        "map_url": l.map_url, "sort_order": l.sort_order, "is_active": l.is_active
    } for l in locs])


@event_page_bp.route("/api/events/<int:ep_id>/pickup-locations", methods=["POST"])
def api_location_create(ep_id):
    ep = EventPage.query.get_or_404(ep_id)
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name 必填"}), 400
    loc = EventPickupLocation(
        event_page_id=ep.id,
        name=name,
        address=(data.get("address") or "").strip() or None,
        map_url=(data.get("map_url") or "").strip() or None,
        sort_order=int(data.get("sort_order") or 0),
        is_active=bool(data.get("is_active", True)),
    )
    db.session.add(loc)
    db.session.commit()
    return jsonify({"id": loc.id, "name": loc.name}), 201


@event_page_bp.route("/api/events/<int:ep_id>/pickup-locations/<int:loc_id>", methods=["PUT"])
def api_location_update(ep_id, loc_id):
    loc = EventPickupLocation.query.filter_by(id=loc_id, event_page_id=ep_id).first_or_404()
    data = request.get_json(force=True) or {}
    if "name"       in data: loc.name       = data["name"].strip()
    if "address"    in data: loc.address    = (data["address"] or "").strip() or None
    if "map_url"    in data: loc.map_url    = (data["map_url"] or "").strip() or None
    if "sort_order" in data: loc.sort_order = int(data["sort_order"])
    if "is_active"  in data: loc.is_active  = bool(data["is_active"])
    db.session.commit()
    return jsonify({"ok": True})


@event_page_bp.route("/api/events/<int:ep_id>/pickup-locations/<int:loc_id>", methods=["DELETE"])
def api_location_delete(ep_id, loc_id):
    loc = EventPickupLocation.query.filter_by(id=loc_id, event_page_id=ep_id).first_or_404()
    db.session.delete(loc)
    db.session.commit()
    return jsonify({"ok": True})


# ── 價格規則 ──────────────────────────────────────────────────────────────────

@event_page_bp.route("/api/events/<int:ep_id>/price-rules", methods=["GET"])
def api_price_rules_list(ep_id):
    ep = EventPage.query.get_or_404(ep_id)
    rules = EventPriceRule.query.filter_by(event_page_id=ep.id).all()
    return jsonify([{
        "id": r.id, "booking_date_id": r.booking_date_id, "location_id": r.location_id,
        "price": r.price, "deposit": r.deposit, "label": r.label
    } for r in rules])


@event_page_bp.route("/api/events/<int:ep_id>/price-rules", methods=["POST"])
def api_price_rule_create(ep_id):
    ep = EventPage.query.get_or_404(ep_id)
    data = request.get_json(force=True) or {}
    price = data.get("price")
    if price is None:
        return jsonify({"error": "price 必填"}), 400
    rule = EventPriceRule(
        event_page_id=ep.id,
        booking_date_id=int(data["booking_date_id"]) if data.get("booking_date_id") else None,
        location_id=int(data["location_id"]) if data.get("location_id") else None,
        price=int(price),
        deposit=int(data.get("deposit") or 0),
        label=(data.get("label") or "").strip() or None,
    )
    db.session.add(rule)
    db.session.commit()
    return jsonify({"id": rule.id}), 201


@event_page_bp.route("/api/events/<int:ep_id>/price-rules/<int:rule_id>", methods=["PUT"])
def api_price_rule_update(ep_id, rule_id):
    rule = EventPriceRule.query.filter_by(id=rule_id, event_page_id=ep_id).first_or_404()
    data = request.get_json(force=True) or {}
    if "price"           in data: rule.price           = int(data["price"])
    if "deposit"         in data: rule.deposit         = int(data["deposit"])
    if "label"           in data: rule.label           = (data["label"] or "").strip() or None
    if "booking_date_id" in data: rule.booking_date_id = int(data["booking_date_id"]) if data["booking_date_id"] else None
    if "location_id"     in data: rule.location_id     = int(data["location_id"]) if data["location_id"] else None
    db.session.commit()
    return jsonify({"ok": True})


@event_page_bp.route("/api/events/<int:ep_id>/price-rules/<int:rule_id>", methods=["DELETE"])
def api_price_rule_delete(ep_id, rule_id):
    rule = EventPriceRule.query.filter_by(id=rule_id, event_page_id=ep_id).first_or_404()
    db.session.delete(rule)
    db.session.commit()
    return jsonify({"ok": True})


# ── 表單欄位設定 ──────────────────────────────────────────────────────────────

@event_page_bp.route("/api/events/<int:ep_id>/form-config", methods=["GET"])
def api_form_config_list(ep_id):
    ep = EventPage.query.get_or_404(ep_id)
    configs = _EFC.query.filter_by(event_page_id=ep.id).all()
    return jsonify([{
        "id": c.id, "field_name": c.field_name,
        "is_visible": c.is_visible, "is_required": c.is_required,
        "label_override": c.label_override
    } for c in configs])


@event_page_bp.route("/api/events/<int:ep_id>/form-config", methods=["POST"])
def api_form_config_upsert(ep_id):
    """批次更新：傳入 [{field_name, is_visible, is_required, label_override}]"""
    ep = EventPage.query.get_or_404(ep_id)
    items = request.get_json(force=True) or []
    for item in items:
        field = (item.get("field_name") or "").strip()
        if not field:
            continue
        cfg = _EFC.query.filter_by(event_page_id=ep.id, field_name=field).first()
        if not cfg:
            cfg = _EFC(event_page_id=ep.id, field_name=field)
            db.session.add(cfg)
        cfg.is_visible  = bool(item.get("is_visible", True))
        cfg.is_required = bool(item.get("is_required", False))
        cfg.label_override = (item.get("label_override") or "").strip() or None
    db.session.commit()
    return jsonify({"ok": True})


# ── EventPage 擴充欄位儲存（booking_config 頁籤） ────────────────────────────

@event_page_bp.route("/api/events/<int:ep_id>/booking-config", methods=["POST"])
def api_booking_config_save(ep_id):
    ep = EventPage.query.get_or_404(ep_id)
    data = request.get_json(force=True) or {}

    def _int_or_none(v):
        try: return int(v) if v not in (None, "") else None
        except (ValueError, TypeError): return None

    def _str_or_none(v):
        return v.strip() or None if v else None

    ep.min_group_size        = _int_or_none(data.get("min_group_size")) or 1
    ep.max_group_size        = _int_or_none(data.get("max_group_size"))
    ep.max_capacity          = _int_or_none(data.get("max_capacity"))
    ep.seats_per_vehicle     = _int_or_none(data.get("seats_per_vehicle")) or 9
    ep.deposit_required      = bool(data.get("deposit_required", True))
    ep.balance_payment_method = _str_or_none(data.get("balance_payment_method")) or "transfer"
    ep.purchase_notes        = _str_or_none(data.get("purchase_notes"))
    ep.cancellation_policy   = _str_or_none(data.get("cancellation_policy"))
    ep.riding_rules          = _str_or_none(data.get("riding_rules"))

    db.session.commit()
    return jsonify({"ok": True})
