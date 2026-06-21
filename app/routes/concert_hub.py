"""
Concert Data Hub Blueprint

後台頁面：
  GET  /admin/concert-hub       — Hub 資料列表
  GET  /admin/concert-conflicts — 衝突管理

API：
  GET  /api/concert-hub          — JSON 列表
  GET  /api/concert-conflicts    — JSON 衝突列表
  POST /api/concert-hub/rebuild  — 完整重建 Hub
"""
from flask import Blueprint, jsonify, render_template, request, session, redirect

from app.models.concert_data_hub import ConcertDataHub

hub_bp = Blueprint("concert_hub", __name__)


def _require_admin():
    if not session.get("admin_id"):
        return None, (jsonify({"error": "未登入"}), 401)
    return True, None


def _require_admin_page():
    if not session.get("admin_id"):
        return redirect("/admin/login")
    return None


# ── 後台頁面 ─────────────────────────────────────────────────────────────────

@hub_bp.route("/admin/concert-hub")
def hub_index():
    guard = _require_admin_page()
    if guard:
        return guard

    hubs = (
        ConcertDataHub.query
        .filter_by(status="active")
        .order_by(ConcertDataHub.confidence_score.desc(), ConcertDataHub.event_date.asc())
        .all()
    )
    total       = len(hubs)
    high_conf   = sum(1 for h in hubs if h.confidence_score >= 80)
    conflicts   = sum(1 for h in hubs if h.has_conflict)

    return render_template(
        "admin/concert_hub/index.html",
        hubs=hubs,
        total=total,
        high_conf=high_conf,
        conflicts=conflicts,
    )


@hub_bp.route("/admin/concert-conflicts")
def hub_conflicts():
    guard = _require_admin_page()
    if guard:
        return guard

    from app.services.concert_conflict_service import get_all_conflicts, conflict_label
    conflict_list = get_all_conflicts()
    return render_template(
        "admin/concert_hub/conflicts.html",
        conflicts=conflict_list,
        conflict_label=conflict_label,
    )


# ── API ───────────────────────────────────────────────────────────────────────

@hub_bp.route("/api/concert-hub")
def api_hub_list():
    ok, err = _require_admin()
    if not ok:
        return err

    page     = request.args.get("page",     1,   type=int)
    per_page = request.args.get("per_page", 50,  type=int)
    city     = request.args.get("city",     None)
    min_conf = request.args.get("min_conf", 0,   type=int)

    q = ConcertDataHub.query.filter_by(status="active")
    if city:
        q = q.filter(ConcertDataHub.city == city)
    if min_conf:
        q = q.filter(ConcertDataHub.confidence_score >= min_conf)

    total = q.count()
    items = (
        q.order_by(ConcertDataHub.confidence_score.desc(), ConcertDataHub.event_date.asc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return jsonify({
        "total": total,
        "page":  page,
        "items": [_hub_to_dict(h) for h in items],
    })


@hub_bp.route("/api/concert-conflicts")
def api_conflicts():
    ok, err = _require_admin()
    if not ok:
        return err

    from app.services.concert_conflict_service import get_all_conflicts
    return jsonify(get_all_conflicts())


@hub_bp.route("/api/concert-hub/rebuild", methods=["POST"])
def api_hub_rebuild():
    ok, err = _require_admin()
    if not ok:
        return err

    try:
        from app.services.concert_data_hub_service import rebuild
        result = rebuild()
        return jsonify({"status": "ok", **result}), 200
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500


# ── 工具 ──────────────────────────────────────────────────────────────────────

def _hub_to_dict(h: ConcertDataHub) -> dict:
    return {
        "id":               h.id,
        "concert_id":       h.concert_id,
        "artist_name":      h.artist_name,
        "concert_name":     h.concert_name,
        "event_date":       str(h.event_date) if h.event_date else None,
        "venue":            h.venue,
        "city":             h.city,
        "source_count":     h.source_count,
        "source_types":     h.source_types,
        "confidence_score": h.confidence_score,
        "confidence_label": h.confidence_label,
        "has_conflict":     h.has_conflict,
        "conflict_types":   h.conflict_types,
        "status":           h.status,
        "updated_at":       h.updated_at.isoformat() if h.updated_at else None,
    }
