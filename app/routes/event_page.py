"""
活動模板系統 Blueprint

後台：/admin/event-pages/*
前台：/events/<slug>
"""
import json
import re
from datetime import datetime

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, session, url_for

from app import db
from app.models.event_page import EventPage
from app.models.event_section import EventSection
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
        hero_variant=request.form.get("hero_variant", "modern-card") or "modern-card",
        tour_name=request.form.get("tour_name", "").strip() or None,
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
    ep.hero_variant   = request.form.get("hero_variant", ep.hero_variant or "modern-card") or "modern-card"
    ep.tour_name      = request.form.get("tour_name", "").strip() or None
    ep.concert_id     = int(request.form.get("concert_id") or 0) or None
    ep.event_group_id = int(request.form.get("event_group_id") or 0) or None
    ep.updated_at     = datetime.utcnow()
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


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 2/3  活動區塊系統
# ══════════════════════════════════════════════════════════════════════════════

# ── 後台：區塊列表 + 新增 ──────────────────────────────────────────────────

@event_page_bp.route("/admin/events/<int:ep_id>/sections", methods=["GET", "POST"])
def ep_sections(ep_id):
    guard = _require_admin()
    if guard:
        return guard

    ep = EventPage.query.get_or_404(ep_id)

    if request.method == "POST":
        section_type = request.form.get("type", "").strip()
        if section_type not in EventSection.TYPES:
            flash("不支援的區塊類型。", "error")
            return redirect(url_for("event_page.ep_sections", ep_id=ep_id))

        # 自動填入預設 content
        default_content = EventSection.TYPE_DEFAULTS.get(section_type, {})
        title = request.form.get("title", "").strip() or None
        content_raw = request.form.get("content_json", "").strip()
        try:
            content = json.loads(content_raw) if content_raw else default_content
        except json.JSONDecodeError:
            content = default_content

        max_order = db.session.query(db.func.max(EventSection.sort_order)).filter_by(event_id=ep_id).scalar() or 0
        sec = EventSection(
            event_id=ep_id,
            type=section_type,
            title=title,
            sort_order=max_order + 1,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        sec.content = content
        db.session.add(sec)
        db.session.commit()
        flash(f"已新增「{sec.type_label}」區塊。", "success")
        return redirect(url_for("event_page.ep_sections", ep_id=ep_id))

    sections = ep.sections.all()
    return render_template("admin/event_pages/sections.html",
                           ep=ep, sections=sections,
                           section_types=EventSection.TYPES,
                           type_labels=EventSection.TYPE_LABELS)


# ── 後台：編輯區塊 ─────────────────────────────────────────────────────────

@event_page_bp.route("/admin/events/<int:ep_id>/sections/<int:sec_id>/edit",
                     methods=["GET", "POST"])
def ep_section_edit(ep_id, sec_id):
    guard = _require_admin()
    if guard:
        return guard

    ep  = EventPage.query.get_or_404(ep_id)
    sec = EventSection.query.get_or_404(sec_id)
    if sec.event_id != ep_id:
        abort(404)

    if request.method == "POST":
        sec.title = request.form.get("title", "").strip() or None
        content_raw = request.form.get("content_json", "").strip()
        try:
            sec.content = json.loads(content_raw) if content_raw else sec.content
        except json.JSONDecodeError:
            flash("JSON 格式錯誤，未儲存 content。", "warning")
        sec.updated_at = datetime.utcnow()
        db.session.commit()
        flash("已更新區塊。", "success")
        return redirect(url_for("event_page.ep_sections", ep_id=ep_id))

    return render_template("admin/event_pages/section_edit.html",
                           ep=ep, sec=sec,
                           type_labels=EventSection.TYPE_LABELS)


# ── 後台：刪除區塊 ─────────────────────────────────────────────────────────

@event_page_bp.route("/admin/events/<int:ep_id>/sections/<int:sec_id>/delete",
                     methods=["POST"])
def ep_section_delete(ep_id, sec_id):
    guard = _require_admin()
    if guard:
        return guard

    sec = EventSection.query.get_or_404(sec_id)
    if sec.event_id != ep_id:
        abort(404)
    db.session.delete(sec)
    db.session.commit()
    flash("已刪除區塊。", "success")
    return redirect(url_for("event_page.ep_sections", ep_id=ep_id))


# ── 後台：啟用/停用區塊 ────────────────────────────────────────────────────

@event_page_bp.route("/admin/events/<int:ep_id>/sections/<int:sec_id>/toggle",
                     methods=["POST"])
def ep_section_toggle(ep_id, sec_id):
    guard = _require_admin()
    if guard:
        return guard

    sec = EventSection.query.get_or_404(sec_id)
    if sec.event_id != ep_id:
        abort(404)
    sec.is_active = not sec.is_active
    sec.updated_at = datetime.utcnow()
    db.session.commit()
    state = "啟用" if sec.is_active else "停用"
    return jsonify({"ok": True, "is_active": sec.is_active, "msg": f"已{state}"})


# ── 後台：更新排序 ─────────────────────────────────────────────────────────

@event_page_bp.route("/admin/events/<int:ep_id>/sections/reorder", methods=["POST"])
def ep_section_reorder(ep_id):
    guard = _require_admin()
    if guard:
        return jsonify({"error": "未登入"}), 401

    data = request.get_json(silent=True) or {}
    order_list = data.get("order", [])   # [{id: 1}, {id: 2}, ...]
    for idx, item in enumerate(order_list):
        sec = EventSection.query.get(item.get("id"))
        if sec and sec.event_id == ep_id:
            sec.sort_order = idx
    db.session.commit()
    return jsonify({"ok": True})


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
        hero_variant=src.hero_variant,
        tour_name=src.tour_name,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.session.add(clone)
    db.session.flush()   # 取得 clone.id

    # 複製 event_sections
    for sec in src.sections.all():
        new_sec = EventSection(
            event_id=clone.id,
            type=sec.type,
            title=sec.title,
            content_json=sec.content_json,
            sort_order=sec.sort_order,
            is_active=sec.is_active,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.session.add(new_sec)

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
