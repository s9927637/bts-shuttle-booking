"""
演唱會商機分析平台 — 後台 Blueprint
URL prefix: /admin/concerts
"""
from datetime import date, datetime

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from app import db
from app.models.concert import Concert, ConcertMetrics, ConcertOpportunity, EventGroup
from app.models.event_page import EventPage

concert_bp = Blueprint("concert", __name__, url_prefix="/admin/concerts")

# ── 登入守衛（沿用 admin session 機制） ────────────────────────────────────────
from flask import session

def _require_admin():
    if not session.get("admin_logged_in"):
        return redirect("/admin/login")
    return None

# ── Mock 商機分析資料（先以 Mock Data 實作） ───────────────────────────────────
_MOCK_ANALYSIS = {
    "BTS":    {"popularity_score": 9.8, "opportunity_score": 9.5, "est_passengers": 320, "est_revenue": 640000},
    "BLACKPINK": {"popularity_score": 9.2, "opportunity_score": 8.8, "est_passengers": 280, "est_revenue": 560000},
    "TWICE":  {"popularity_score": 8.5, "opportunity_score": 8.0, "est_passengers": 200, "est_revenue": 400000},
    "aespa":  {"popularity_score": 7.8, "opportunity_score": 7.5, "est_passengers": 160, "est_revenue": 320000},
    "IVE":    {"popularity_score": 7.5, "opportunity_score": 7.2, "est_passengers": 140, "est_revenue": 280000},
}

def _mock_metrics(artist: str) -> dict:
    return _MOCK_ANALYSIS.get(artist, {
        "popularity_score": 6.0,
        "opportunity_score": 5.5,
        "est_passengers": 80,
        "est_revenue": 160000,
    })


# ── 演唱會列表 ─────────────────────────────────────────────────────────────────

@concert_bp.route("/")
def concert_list():
    guard = _require_admin()
    if guard: return guard

    q = request.args.get("q", "").strip()
    query = Concert.query.order_by(Concert.concert_date.asc())
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(Concert.artist.ilike(like), Concert.name.ilike(like), Concert.city.ilike(like))
        )
    concerts = query.all()
    return render_template("admin/concerts/list.html", concerts=concerts, q=q)


@concert_bp.route("/create", methods=["POST"])
def concert_create():
    guard = _require_admin()
    if guard: return guard

    artist = request.form.get("artist", "").strip()
    name   = request.form.get("name", "").strip()
    if not artist or not name:
        flash("藝人與演唱會名稱為必填。", "error")
        return redirect(url_for("concert.concert_list"))

    date_str = request.form.get("concert_date", "")
    concert_date = None
    if date_str:
        try:
            concert_date = date.fromisoformat(date_str)
        except ValueError:
            pass

    c = Concert(
        artist=artist,
        name=name,
        concert_date=concert_date,
        city=request.form.get("city", "").strip() or None,
        venue=request.form.get("venue", "").strip() or None,
        status=request.form.get("status", "評估中"),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.session.add(c)
    db.session.flush()

    # 自動填入 Mock 分析資料
    mock = _mock_metrics(artist)
    m = ConcertMetrics(
        concert_id=c.id,
        popularity_score=mock["popularity_score"],
        opportunity_score=mock["opportunity_score"],
        est_passengers=mock["est_passengers"],
        est_revenue=mock["est_revenue"],
        updated_at=datetime.utcnow(),
    )
    db.session.add(m)
    db.session.commit()
    flash(f"已新增演唱會「{name}」。", "success")
    return redirect(url_for("concert.concert_list"))


@concert_bp.route("/<int:concert_id>/edit", methods=["POST"])
def concert_edit(concert_id):
    guard = _require_admin()
    if guard: return guard

    c = Concert.query.get_or_404(concert_id)
    c.artist = request.form.get("artist", c.artist).strip()
    c.name   = request.form.get("name",   c.name).strip()
    c.city   = request.form.get("city",   "").strip() or None
    c.venue  = request.form.get("venue",  "").strip() or None
    c.status = request.form.get("status", c.status)
    c.updated_at = datetime.utcnow()

    date_str = request.form.get("concert_date", "")
    if date_str:
        try:
            c.concert_date = date.fromisoformat(date_str)
        except ValueError:
            pass
    else:
        c.concert_date = None

    db.session.commit()
    flash(f"已更新演唱會「{c.name}」。", "success")
    return redirect(url_for("concert.concert_list"))


# ── 商機分析 ───────────────────────────────────────────────────────────────────

@concert_bp.route("/opportunities")
def opportunities():
    guard = _require_admin()
    if guard: return guard

    concerts = Concert.query.order_by(Concert.concert_date.asc()).all()

    # 為尚無 metrics 的演唱會補上 Mock 資料（不寫入 DB）
    analysis = []
    for c in concerts:
        m = c.metrics
        if m:
            analysis.append({
                "concert": c,
                "popularity_score":  m.popularity_score or 0,
                "opportunity_score": m.opportunity_score or 0,
                "est_passengers":    m.est_passengers or 0,
                "est_revenue":       m.est_revenue or 0,
            })
        else:
            mock = _mock_metrics(c.artist)
            analysis.append({"concert": c, **mock})

    # 依商機分數排序
    analysis.sort(key=lambda x: x["opportunity_score"], reverse=True)
    return render_template("admin/concerts/opportunities.html", analysis=analysis)


# ── 開團管理 ───────────────────────────────────────────────────────────────────

@concert_bp.route("/event-groups")
def event_groups():
    guard = _require_admin()
    if guard: return guard

    groups   = EventGroup.query.order_by(EventGroup.created_at.desc()).all()
    concerts = Concert.query.order_by(Concert.concert_date.asc()).all()
    return render_template("admin/concerts/event_groups.html", groups=groups, concerts=concerts)


@concert_bp.route("/event-groups/create", methods=["POST"])
def event_group_create():
    guard = _require_admin()
    if guard: return guard

    concert_id = request.form.get("concert_id", type=int)
    group_name = request.form.get("group_name", "").strip()
    if not concert_id or not group_name:
        flash("請選擇演唱會並填寫活動名稱。", "error")
        return redirect(url_for("concert.event_groups"))

    Concert.query.get_or_404(concert_id)

    date_str = request.form.get("departure_date", "")
    dep_date = None
    if date_str:
        try:
            dep_date = date.fromisoformat(date_str)
        except ValueError:
            pass

    g = EventGroup(
        concert_id=concert_id,
        group_name=group_name,
        departure_date=dep_date,
        vehicle_type=request.form.get("vehicle_type", "minibus"),
        seat_limit=int(request.form.get("seat_limit", 8) or 8),
        price_per_person=int(request.form.get("price_per_person", 2000) or 2000),
        status=request.form.get("status", "草稿"),
        notes=request.form.get("notes", "").strip() or None,
        created_at=datetime.utcnow(),
    )
    db.session.add(g)
    db.session.commit()
    flash(f"已建立活動群組「{group_name}」。", "success")
    return redirect(url_for("concert.event_groups"))


@concert_bp.route("/event-groups/<int:group_id>/delete", methods=["POST"])
def event_group_delete(group_id):
    guard = _require_admin()
    if guard: return guard

    g = EventGroup.query.get_or_404(group_id)
    name = g.group_name
    db.session.delete(g)
    db.session.commit()
    flash(f"已刪除活動群組「{name}」。", "success")
    return redirect(url_for("concert.event_groups"))


# ── 待開團：尚未建立 EventPage 的演唱會 ───────────────────────────────────────

@concert_bp.route("/pending")
def pending():
    guard = _require_admin()
    if guard: return guard

    # 取得有 concert_id 的 EventPage concert_id 集合（未軟刪除）
    linked_ids = {
        row[0] for row in
        db.session.query(EventPage.concert_id)
        .filter(EventPage.concert_id.isnot(None), EventPage.deleted_at.is_(None))
        .all()
    }
    concerts = (
        Concert.query
        .filter(Concert.id.notin_(linked_ids) if linked_ids else db.true())
        .order_by(Concert.concert_date.asc())
        .all()
    )
    return render_template("admin/concerts/pending.html", concerts=concerts)


# ── 已開團：已建立 EventPage 的演唱會 ─────────────────────────────────────────

@concert_bp.route("/active")
def active():
    guard = _require_admin()
    if guard: return guard

    event_pages = (
        EventPage.query
        .filter(EventPage.concert_id.isnot(None), EventPage.deleted_at.is_(None))
        .order_by(EventPage.created_at.desc())
        .all()
    )
    return render_template("admin/concerts/active.html", event_pages=event_pages)


# ── API: 一鍵建立 EventPage ───────────────────────────────────────────────────

@concert_bp.route("/<int:concert_id>/create-event", methods=["POST"])
def api_create_event(concert_id):
    if not session.get("admin_logged_in"):
        return jsonify({"error": "未登入"}), 401

    concert = Concert.query.get_or_404(concert_id)

    from app.services.event_builder import build_event_from_concert, EventAlreadyExists
    try:
        ep = build_event_from_concert(concert)
        db.session.commit()
        return jsonify({"success": True, "event_id": ep.id, "slug": ep.slug})
    except EventAlreadyExists as e:
        return jsonify({
            "success": False,
            "error": "已建立活動",
            "event_id": e.event_page.id,
            "slug": e.event_page.slug,
        }), 409
