"""
Passenger Operations Center Blueprint

Pages:
  GET  /admin/passengers            → 乘客列表
  GET  /admin/passengers/<id>       → 乘客詳情
  POST /admin/passengers/sync       → 同步所有乘客 Profile
  POST /admin/passengers/<id>/tags/add    → 新增標籤
  POST /admin/passengers/<id>/tags/remove → 移除標籤

APIs:
  GET  /api/passengers              → 列表 JSON
  GET  /api/passengers/statistics   → 統計 JSON
  GET  /api/passengers/<id>         → 詳情 JSON
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session

from app import db
from app.services.passenger_service import (
    sync_all_passengers, sync_passenger,
    get_passenger_list, get_passenger_detail,
    get_passenger_statistics,
    add_tag, remove_tag,
)

passenger_center_bp = Blueprint("passenger_center", __name__)

PER_PAGE = 25


def _require_admin():
    if not session.get("admin_id"):
        return redirect(url_for("auth.login_page"))


# ── 列表 ──────────────────────────────────────────────────────────────────────

@passenger_center_bp.route("/admin/passengers")
def pc_index():
    guard = _require_admin()
    if guard:
        return guard

    q    = request.args.get("q", "").strip()
    tag  = request.args.get("tag", "").strip()
    page = max(1, request.args.get("page", 1, type=int))

    result = get_passenger_list(q=q, tag=tag, page=page, per_page=PER_PAGE)
    stats  = get_passenger_statistics()

    return render_template(
        "admin/passenger_center/index.html",
        **result,
        stats=stats,
        q=q,
        current_tag=tag,
        predefined_tags=["VIP", "高回購", "未付款", "黑名單", "高價值客戶", "常客", "新客"],
    )


# ── 詳情 ──────────────────────────────────────────────────────────────────────

@passenger_center_bp.route("/admin/passengers/<int:passenger_id>")
def pc_detail(passenger_id):
    guard = _require_admin()
    if guard:
        return guard

    detail = get_passenger_detail(passenger_id)
    return render_template("admin/passenger_center/detail.html", **detail)


# ── 同步 Profile ───────────────────────────────────────────────────────────────

@passenger_center_bp.route("/admin/passengers/sync", methods=["POST"])
def pc_sync():
    guard = _require_admin()
    if guard:
        return guard

    result = sync_all_passengers()
    flash(
        f"同步完成：共 {result['synced']} 位乘客，"
        f"新建 {result['created']}、更新 {result['updated']}。",
        "success",
    )
    return redirect(url_for("passenger_center.pc_index"))


# ── 新增標籤 ──────────────────────────────────────────────────────────────────

@passenger_center_bp.route("/admin/passengers/<int:passenger_id>/tags/add", methods=["POST"])
def pc_add_tag(passenger_id):
    guard = _require_admin()
    if guard:
        return guard

    tag_name = request.form.get("tag_name", "").strip()
    ok, msg  = add_tag(passenger_id, tag_name)
    if ok:
        db.session.commit()
        flash(f"標籤「{tag_name}」已新增。", "success")
    else:
        flash(msg, "error")
    return redirect(url_for("passenger_center.pc_detail", passenger_id=passenger_id))


# ── 移除標籤 ──────────────────────────────────────────────────────────────────

@passenger_center_bp.route("/admin/passengers/<int:passenger_id>/tags/remove", methods=["POST"])
def pc_remove_tag(passenger_id):
    guard = _require_admin()
    if guard:
        return guard

    tag_name = request.form.get("tag_name", "").strip()
    ok, msg  = remove_tag(passenger_id, tag_name)
    if ok:
        db.session.commit()
        flash(f"標籤「{tag_name}」已移除。", "success")
    else:
        flash(msg, "error")
    return redirect(url_for("passenger_center.pc_detail", passenger_id=passenger_id))


# ══ API ═══════════════════════════════════════════════════════════════════════

@passenger_center_bp.route("/api/passengers")
def api_passengers():
    guard = _require_admin()
    if guard:
        return jsonify({"error": "Unauthorized"}), 401

    q    = request.args.get("q", "").strip()
    tag  = request.args.get("tag", "").strip()
    page = max(1, request.args.get("page", 1, type=int))

    result = get_passenger_list(q=q, tag=tag, page=page, per_page=50)
    return jsonify({
        "passengers": [
            {
                "id":           p.id,
                "name":         p.name,
                "phone":        p.phone,
                "line_user_id": p.line_user_id,
                "total_orders": p.total_orders,
                "total_events": p.total_events,
                "total_spent":  p.total_spent,
                "tags":         p.tag_names,
                "last_order_at":p.last_order_at.strftime("%Y-%m-%d %H:%M") if p.last_order_at else None,
                "is_vip":       p.is_vip,
            }
            for p in result["items"]
        ],
        "total": result["total"],
        "page":  result["page"],
        "pages": result["pages"],
    })


@passenger_center_bp.route("/api/passengers/statistics")
def api_passenger_statistics():
    guard = _require_admin()
    if guard:
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify(get_passenger_statistics())


@passenger_center_bp.route("/api/passengers/<int:passenger_id>")
def api_passenger_detail(passenger_id):
    guard = _require_admin()
    if guard:
        return jsonify({"error": "Unauthorized"}), 401

    detail  = get_passenger_detail(passenger_id)
    profile = detail["profile"]

    def _order_dict(o):
        return {
            "id":             o.id,
            "order_no":       o.order_no,
            "departure_date": o.departure_date,
            "passenger_count":o.passenger_count,
            "total_amount":   o.total_amount,
            "payment_status": o.payment_status,
            "event_title":    o.event_page.title if o.event_page else "BTS 高雄演唱會",
            "created_at":     o.created_at.strftime("%Y-%m-%d %H:%M") if o.created_at else None,
        }

    return jsonify({
        "profile": {
            "id":           profile.id,
            "name":         profile.name,
            "phone":        profile.phone,
            "line_user_id": profile.line_user_id,
            "total_orders": profile.total_orders,
            "total_events": profile.total_events,
            "total_spent":  profile.total_spent,
            "tags":         profile.tag_names,
            "is_vip":       profile.is_vip,
            "last_order_at":profile.last_order_at.strftime("%Y-%m-%d %H:%M") if profile.last_order_at else None,
        },
        "orders":        [_order_dict(o) for o in detail["orders"]],
        "events_history":[
            {"title": e["title"], "artist": e["artist"], "order_count": e["order_count"]}
            for e in detail["events_history"]
        ],
    })
