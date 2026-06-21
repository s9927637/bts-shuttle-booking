"""
Multi Event Dispatch Center Blueprint

URL prefix: /admin/event-dispatch

Pages:
  GET  /admin/event-dispatch/           → 排車中心首頁（活動列表）
  GET  /admin/event-dispatch/<id>       → 單一車次詳情 + 乘客清單
  POST /admin/event-dispatch/create     → 建立車次
  POST /admin/event-dispatch/<id>/add-order    → 加入訂單
  POST /admin/event-dispatch/<id>/remove-order → 移除訂單
  POST /admin/event-dispatch/<id>/status       → 更新狀態

APIs:
  GET  /api/dispatch/events             → 列表 JSON
  GET  /api/dispatch/event/<id>         → 詳情 JSON
  POST /api/dispatch/create             → 建立車次 JSON
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session

from app import db
from app.models.event_page import EventPage
from app.services.event_dispatch_service import (
    get_all_dispatch_events,
    get_dispatch_event_detail,
    get_unassigned_orders,
    create_dispatch_event,
    add_order_to_dispatch_event,
    remove_order_from_dispatch_event,
)

event_dispatch_bp = Blueprint("event_dispatch", __name__)

DISPATCH_STATUSES = ["規劃中", "確認中", "已確認", "已出發", "已完成", "已取消"]


def _require_admin():
    if not session.get("admin_id"):
        return redirect(url_for("auth.login_page"))


# ── 首頁：活動車次列表 ─────────────────────────────────────────────────────────

@event_dispatch_bp.route("/admin/event-dispatch/")
@event_dispatch_bp.route("/admin/event-dispatch")
def ed_index():
    guard = _require_admin()
    if guard:
        return guard

    event_filter = request.args.get("event_filter", "").strip()

    ep_id = None
    if event_filter == "bts":
        ep_id = 0
    elif event_filter and event_filter.isdigit():
        ep_id = int(event_filter)

    dispatch_events = get_all_dispatch_events(ep_id)
    event_pages     = EventPage.query.filter(
        EventPage.deleted_at.is_(None)
    ).order_by(EventPage.artist_name, EventPage.created_at.desc()).all()

    return render_template(
        "admin/event_dispatch/index.html",
        dispatch_events=dispatch_events,
        event_pages=event_pages,
        event_filter=event_filter,
        statuses=DISPATCH_STATUSES,
    )


# ── 車次詳情 ──────────────────────────────────────────────────────────────────

@event_dispatch_bp.route("/admin/event-dispatch/<int:dispatch_event_id>")
def ed_detail(dispatch_event_id):
    guard = _require_admin()
    if guard:
        return guard

    detail = get_dispatch_event_detail(dispatch_event_id)
    ep_id  = detail["dispatch_event"].event_page_id
    unassigned = get_unassigned_orders(ep_id)

    return render_template(
        "admin/event_dispatch/detail.html",
        detail=detail,
        unassigned=unassigned,
        statuses=DISPATCH_STATUSES,
    )


# ── 建立車次（HTML POST）──────────────────────────────────────────────────────

@event_dispatch_bp.route("/admin/event-dispatch/create", methods=["POST"])
def ed_create():
    guard = _require_admin()
    if guard:
        return guard

    dispatch_date  = request.form.get("dispatch_date", "").strip()
    event_page_id  = request.form.get("event_page_id", type=int) or None
    departure_city = request.form.get("departure_city", "").strip() or None
    notes          = request.form.get("notes", "").strip() or None

    if not dispatch_date:
        flash("請填寫出車日期。", "error")
        return redirect(url_for("event_dispatch.ed_index"))

    try:
        de = create_dispatch_event(dispatch_date, event_page_id, departure_city, notes)
        db.session.commit()
        flash(f"已建立車次「{de.event_title}」（{dispatch_date}）。", "success")
        return redirect(url_for("event_dispatch.ed_detail", dispatch_event_id=de.id))
    except Exception as exc:
        db.session.rollback()
        flash(f"建立失敗：{exc}", "error")
        return redirect(url_for("event_dispatch.ed_index"))


# ── 加入訂單 ──────────────────────────────────────────────────────────────────

@event_dispatch_bp.route("/admin/event-dispatch/<int:dispatch_event_id>/add-order", methods=["POST"])
def ed_add_order(dispatch_event_id):
    guard = _require_admin()
    if guard:
        return guard

    order_id = request.form.get("order_id", type=int)
    ok, msg  = add_order_to_dispatch_event(dispatch_event_id, order_id)
    db.session.commit()
    flash(msg if not ok else "訂單已加入車次。", "success" if ok else "error")
    return redirect(url_for("event_dispatch.ed_detail", dispatch_event_id=dispatch_event_id))


# ── 移除訂單 ──────────────────────────────────────────────────────────────────

@event_dispatch_bp.route("/admin/event-dispatch/<int:dispatch_event_id>/remove-order", methods=["POST"])
def ed_remove_order(dispatch_event_id):
    guard = _require_admin()
    if guard:
        return guard

    order_id = request.form.get("order_id", type=int)
    ok, msg  = remove_order_from_dispatch_event(dispatch_event_id, order_id)
    db.session.commit()
    flash(msg if not ok else "訂單已移出車次。", "success" if ok else "error")
    return redirect(url_for("event_dispatch.ed_detail", dispatch_event_id=dispatch_event_id))


# ── 更新狀態 ──────────────────────────────────────────────────────────────────

@event_dispatch_bp.route("/admin/event-dispatch/<int:dispatch_event_id>/status", methods=["POST"])
def ed_update_status(dispatch_event_id):
    guard = _require_admin()
    if guard:
        return guard

    from app.models.dispatch_event import DispatchEvent
    from datetime import datetime
    de     = DispatchEvent.query.get_or_404(dispatch_event_id)
    status = request.form.get("status", "").strip()
    if status in DISPATCH_STATUSES:
        de.status     = status
        de.updated_at = datetime.utcnow()
        db.session.commit()
        flash(f"狀態已更新為「{status}」。", "success")
    else:
        flash("無效狀態。", "error")
    return redirect(url_for("event_dispatch.ed_detail", dispatch_event_id=dispatch_event_id))


# ══ API ═══════════════════════════════════════════════════════════════════════

@event_dispatch_bp.route("/api/dispatch/events")
def api_dispatch_events():
    guard = _require_admin()
    if guard:
        return jsonify({"error": "Unauthorized"}), 401

    event_filter = request.args.get("event_filter", "").strip()
    ep_id = None
    if event_filter == "bts":
        ep_id = 0
    elif event_filter and event_filter.isdigit():
        ep_id = int(event_filter)

    events = get_all_dispatch_events(ep_id)
    return jsonify({
        "dispatch_events": [
            {
                "id":             de.id,
                "event_title":    de.event_title,
                "artist_name":    de.artist_name,
                "event_page_id":  de.event_page_id,
                "dispatch_date":  de.dispatch_date,
                "departure_city": de.departure_city,
                "vehicle_count":  de.vehicle_count,
                "passenger_count":de.passenger_count,
                "status":         de.status,
                "created_at":     de.created_at.strftime("%Y-%m-%d %H:%M") if de.created_at else None,
            }
            for de in events
        ],
        "total": len(events),
    })


@event_dispatch_bp.route("/api/dispatch/event/<int:dispatch_event_id>")
def api_dispatch_event_detail(dispatch_event_id):
    guard = _require_admin()
    if guard:
        return jsonify({"error": "Unauthorized"}), 401

    detail = get_dispatch_event_detail(dispatch_event_id)
    de     = detail["dispatch_event"]

    def _order_dict(o):
        return {
            "id":             o.id,
            "order_no":       o.order_no,
            "contact_name":   o.contact_name,
            "phone":          o.phone,
            "passenger_count":o.passenger_count,
            "payment_status": o.payment_status,
            "departure_date": o.departure_date,
            "event_title":    o.event_page.title if o.event_page else "BTS 高雄演唱會",
        }

    return jsonify({
        "dispatch_event": {
            "id":             de.id,
            "event_title":    de.event_title,
            "artist_name":    de.artist_name,
            "dispatch_date":  de.dispatch_date,
            "departure_city": de.departure_city,
            "vehicle_count":  de.vehicle_count,
            "passenger_count":de.passenger_count,
            "status":         de.status,
        },
        "orders":       [_order_dict(o) for o in detail["orders"]],
        "paid_orders":  [_order_dict(o) for o in detail["paid_orders"]],
        "unpaid_orders":[_order_dict(o) for o in detail["unpaid_orders"]],
        "total_pax":    detail["total_pax"],
        "paid_pax":     detail["paid_pax"],
        "unpaid_pax":   detail["unpaid_pax"],
    })


@event_dispatch_bp.route("/api/dispatch/create", methods=["POST"])
def api_dispatch_create():
    guard = _require_admin()
    if guard:
        return jsonify({"error": "Unauthorized"}), 401

    data           = request.get_json() or {}
    dispatch_date  = data.get("dispatch_date", "").strip()
    event_page_id  = data.get("event_page_id") or None
    departure_city = data.get("departure_city") or None
    notes          = data.get("notes") or None

    if not dispatch_date:
        return jsonify({"ok": False, "error": "dispatch_date 必填"}), 400

    try:
        de = create_dispatch_event(dispatch_date, event_page_id, departure_city, notes)
        db.session.commit()
        return jsonify({
            "ok": True,
            "id":            de.id,
            "event_title":   de.event_title,
            "dispatch_date": de.dispatch_date,
        })
    except Exception as exc:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(exc)}), 500
