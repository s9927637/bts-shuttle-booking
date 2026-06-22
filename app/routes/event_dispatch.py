"""
Multi Event Dispatch Center Blueprint

URL prefix: /admin/event-dispatch

Pages:
  GET  /admin/event-dispatch/           → 拖曳看板（event_id + date 篩選）
  POST /admin/event-dispatch/create     → 建立車次
  POST /admin/event-dispatch/move       → 拖曳移動訂單（JSON, CSRF exempt）
  POST /admin/event-dispatch/<id>/delete        → 刪除車次
  POST /admin/event-dispatch/<id>/status        → 更新狀態
  GET  /admin/event-dispatch/<id>       → 車次詳情（乘客清單）
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session

from app import db, csrf
from app.models.event_page import EventPage
from app.models.vehicle import Vehicle
from app.models.driver import Driver
from app.services.event_dispatch_service import (
    get_all_dispatch_events,
    get_dispatch_event_detail,
    get_unassigned_orders,
    create_dispatch_event,
    delete_dispatch_event,
    add_order_to_dispatch_event,
    remove_order_from_dispatch_event,
    move_order_between_events,
    get_departure_dates_for_event,
    get_kanban_data,
)

event_dispatch_bp = Blueprint("event_dispatch", __name__)

DISPATCH_STATUSES = ["規劃中", "確認中", "已確認", "已出發", "已完成", "已取消"]


def _require_admin():
    if not session.get("admin_id"):
        return redirect(url_for("auth.login_page"))


# ── 看板首頁 ──────────────────────────────────────────────────────────────────

@event_dispatch_bp.route("/admin/event-dispatch/")
@event_dispatch_bp.route("/admin/event-dispatch")
def ed_index():
    guard = _require_admin()
    if guard:
        return guard

    event_pages = EventPage.query.filter(
        EventPage.deleted_at.is_(None)
    ).order_by(EventPage.artist_name, EventPage.created_at.desc()).all()

    vehicles = Vehicle.query.order_by(Vehicle.plate_number).all()
    drivers  = Driver.query.order_by(Driver.name).all()

    # 活動篩選
    event_filter = request.args.get("event_id", "").strip()
    if event_filter == "bts":
        ep_id = 0
    elif event_filter and event_filter.isdigit():
        ep_id = int(event_filter)
    else:
        ep_id = None

    # 日期篩選
    departure_dates = get_departure_dates_for_event(ep_id)
    active_date = request.args.get("date", departure_dates[0] if departure_dates else "")

    kanban = get_kanban_data(ep_id, active_date) if active_date else {"unassigned": [], "dispatch_items": []}

    return render_template(
        "admin/event_dispatch/index.html",
        event_pages=event_pages,
        event_filter=event_filter,
        departure_dates=departure_dates,
        active_date=active_date,
        unassigned=kanban["unassigned"],
        dispatch_items=kanban["dispatch_items"],
        vehicles=vehicles,
        drivers=drivers,
        statuses=DISPATCH_STATUSES,
    )


# ── 建立車次 ──────────────────────────────────────────────────────────────────

@event_dispatch_bp.route("/admin/event-dispatch/create", methods=["POST"])
def ed_create():
    guard = _require_admin()
    if guard:
        return guard

    dispatch_date  = request.form.get("dispatch_date", "").strip()
    event_page_id  = request.form.get("event_page_id", type=int) or None
    departure_city = request.form.get("departure_city", "").strip() or None
    vehicle_id     = request.form.get("vehicle_id", type=int) or None
    notes          = request.form.get("notes", "").strip() or None

    event_filter = request.form.get("event_filter", "")

    if not dispatch_date:
        flash("請填寫出車日期。", "error")
        return redirect(url_for("event_dispatch.ed_index",
                                event_id=event_filter, date=dispatch_date))
    try:
        de = create_dispatch_event(dispatch_date, event_page_id, departure_city, notes, vehicle_id)
        db.session.commit()
        flash(f"已建立車次（{dispatch_date}）。", "success")
    except Exception as exc:
        db.session.rollback()
        flash(f"建立失敗：{exc}", "error")

    return redirect(url_for("event_dispatch.ed_index",
                            event_id=event_filter, date=dispatch_date))


# ── 拖曳移動訂單（JSON API, CSRF exempt）─────────────────────────────────────

@event_dispatch_bp.route("/admin/event-dispatch/move", methods=["POST"])
@csrf.exempt
def ed_move():
    guard = _require_admin()
    if guard:
        return jsonify({"ok": False, "error": "未登入"}), 401

    data             = request.get_json() or {}
    order_id         = data.get("order_id")
    target_event_id  = data.get("dispatch_event_id")  # None = 移回待排

    ok, msg = move_order_between_events(order_id, target_event_id)
    if not ok:
        return jsonify({"ok": False, "error": msg}), 400

    db.session.commit()
    return jsonify({"ok": True})


# ── 刪除車次 ──────────────────────────────────────────────────────────────────

@event_dispatch_bp.route("/admin/event-dispatch/<int:dispatch_event_id>/delete", methods=["POST"])
def ed_delete(dispatch_event_id):
    guard = _require_admin()
    if guard:
        return guard

    event_filter = request.form.get("event_filter", "")
    active_date  = request.form.get("date", "")

    try:
        delete_dispatch_event(dispatch_event_id)
        db.session.commit()
        flash("車次已刪除，訂單已移回待排。", "success")
    except Exception as exc:
        db.session.rollback()
        flash(f"刪除失敗：{exc}", "error")

    return redirect(url_for("event_dispatch.ed_index",
                            event_id=event_filter, date=active_date))


# ── 更新狀態 ──────────────────────────────────────────────────────────────────

@event_dispatch_bp.route("/admin/event-dispatch/<int:dispatch_event_id>/status", methods=["POST"])
def ed_update_status(dispatch_event_id):
    guard = _require_admin()
    if guard:
        return guard

    from app.models.dispatch_event import DispatchEvent
    from datetime import datetime

    event_filter = request.form.get("event_filter", "")
    active_date  = request.form.get("date", "")

    de     = DispatchEvent.query.get_or_404(dispatch_event_id)
    status = request.form.get("status", "").strip()
    if status in DISPATCH_STATUSES:
        de.status     = status
        de.updated_at = datetime.utcnow()
        db.session.commit()
        flash(f"狀態已更新為「{status}」。", "success")
    else:
        flash("無效狀態。", "error")

    return redirect(url_for("event_dispatch.ed_index",
                            event_id=event_filter, date=active_date))


# ── 車次詳情 ──────────────────────────────────────────────────────────────────

@event_dispatch_bp.route("/admin/event-dispatch/<int:dispatch_event_id>")
def ed_detail(dispatch_event_id):
    guard = _require_admin()
    if guard:
        return guard

    detail     = get_dispatch_event_detail(dispatch_event_id)
    ep_id      = detail["dispatch_event"].event_page_id
    unassigned = get_unassigned_orders(ep_id)

    return render_template(
        "admin/event_dispatch/detail.html",
        detail=detail,
        unassigned=unassigned,
        statuses=DISPATCH_STATUSES,
    )


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
