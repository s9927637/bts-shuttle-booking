"""
活動模板系統 Blueprint

後台：/admin/event-pages/*
前台：/events/<slug>
"""
import re
from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

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
        # 非發布狀態：後台管理員可預覽，一般訪客看 404
        if not session.get("admin_id"):
            abort(404)
    return render_template("passenger/event_template.html", ep=ep)
