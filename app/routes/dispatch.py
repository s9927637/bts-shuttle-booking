from flask import Blueprint, session, redirect, render_template, request, flash, url_for, jsonify
from app import db
from app.models.order import Order
from app.models.vehicle import Vehicle
from app.models.driver import Driver
from app.models.dispatch import Dispatch, DispatchOrder
from app.services.dispatch_service import (
    auto_dispatch, create_dispatch, assign_order,
    calculate_capacity, remove_order_from_dispatch, move_order_to_dispatch,
)

dispatch_bp = Blueprint("dispatch", __name__, url_prefix="/admin/dispatch")

DEPARTURE_OPTIONS = ["11/19(四)", "11/21(六)", "11/22(日)"]
MAX_CAPACITY = 8


def require_admin():
    if not session.get("admin_id"):
        return redirect(url_for("auth.login_page"))


# ── 主頁面 ─────────────────────────────────────────────────────────────────

@dispatch_bp.route("/")
def index():
    guard = require_admin()
    if guard:
        return guard

    active_date = request.args.get("date", DEPARTURE_OPTIONS[0])

    # 待排車訂單：已付款 + 未排車
    unassigned = (
        Order.query
        .filter_by(departure_date=active_date, payment_status="已付款")
        .filter(Order.dispatch_id.is_(None))
        .order_by(Order.created_at.asc())
        .all()
    )

    # 該日期所有 dispatches
    dispatches = (
        Dispatch.query
        .filter_by(departure_date=active_date)
        .order_by(Dispatch.created_at.asc())
        .all()
    )

    # 為每個 dispatch 計算目前人數
    dispatch_data = []
    for d in dispatches:
        orders = [do.order for do in d.dispatch_orders if do.order]
        current = sum(o.passenger_count for o in orders)
        dispatch_data.append({
            "dispatch":  d,
            "orders":    orders,
            "current":   current,
            "max":       MAX_CAPACITY,
            "full":      current >= MAX_CAPACITY,
        })

    vehicles = Vehicle.query.order_by(Vehicle.plate_number).all()
    drivers  = Driver.query.order_by(Driver.name).all()

    return render_template(
        "admin/dispatch.html",
        active_date=active_date,
        departure_options=DEPARTURE_OPTIONS,
        unassigned=unassigned,
        dispatch_data=dispatch_data,
        vehicles=vehicles,
        drivers=drivers,
        max_capacity=MAX_CAPACITY,
    )


# ── 自動排車 ────────────────────────────────────────────────────────────────

@dispatch_bp.route("/auto", methods=["POST"])
def auto():
    guard = require_admin()
    if guard:
        return guard

    date   = request.form.get("date", DEPARTURE_OPTIONS[0])
    result = auto_dispatch(date)
    flash(
        f"自動排車完成：建立 {result['dispatches_created']} 台車，"
        f"分配 {result['orders_assigned']} 筆訂單。",
        "success",
    )
    return redirect(url_for("dispatch.index", date=date))


# ── 手動建立 dispatch ────────────────────────────────────────────────────────

@dispatch_bp.route("/create", methods=["POST"])
def create():
    guard = require_admin()
    if guard:
        return guard

    date       = request.form.get("date")
    vehicle_id = request.form.get("vehicle_id", type=int)
    driver_id  = request.form.get("driver_id", type=int) or None

    if not date or not vehicle_id:
        flash("請選擇日期與車輛。", "error")
        return redirect(url_for("dispatch.index", date=date))

    try:
        d = create_dispatch(date, vehicle_id, driver_id)
        db.session.commit()
        flash(f"已建立排車記錄（Dispatch #{d.id}）。", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"建立失敗：{e}", "error")

    return redirect(url_for("dispatch.index", date=date))


# ── 指派訂單到 dispatch ─────────────────────────────────────────────────────

@dispatch_bp.route("/assign", methods=["POST"])
def assign():
    guard = require_admin()
    if guard:
        return guard

    dispatch_id = request.form.get("dispatch_id", type=int)
    order_id    = request.form.get("order_id",    type=int)
    date        = request.form.get("date", DEPARTURE_OPTIONS[0])

    dispatch = Dispatch.query.get_or_404(dispatch_id)
    order    = Order.query.get_or_404(order_id)

    if order.payment_status != "已付款":
        flash("只有已付款訂單才可排車。", "error")
        return redirect(url_for("dispatch.index", date=date))

    if not assign_order(dispatch, order):
        flash(f"車輛已滿（最多 {MAX_CAPACITY} 人），無法加入此訂單。", "error")
    else:
        db.session.commit()
        flash(f"訂單 {order.order_no} 已排入 Dispatch #{dispatch_id}。", "success")

    return redirect(url_for("dispatch.index", date=date))


# ── 從 dispatch 移除訂單 ────────────────────────────────────────────────────

@dispatch_bp.route("/remove-order", methods=["POST"])
def remove_order():
    guard = require_admin()
    if guard:
        return guard

    order_id = request.form.get("order_id", type=int)
    date     = request.form.get("date", DEPARTURE_OPTIONS[0])
    order    = Order.query.get_or_404(order_id)

    remove_order_from_dispatch(order)
    flash(f"訂單 {order.order_no} 已移回待排車。", "success")
    return redirect(url_for("dispatch.index", date=date))


# ── Drag & Drop：移動訂單至另一 dispatch（JSON API）──────────────────────────

@dispatch_bp.route("/move", methods=["POST"])
def move():
    guard = require_admin()
    if guard:
        return jsonify({"ok": False, "error": "未登入"}), 401

    data        = request.get_json()
    order_id    = data.get("order_id")
    dispatch_id = data.get("dispatch_id")  # None = 移回待排車

    order = Order.query.get(order_id)
    if not order:
        return jsonify({"ok": False, "error": "訂單不存在"}), 404

    if dispatch_id is None:
        remove_order_from_dispatch(order)
        return jsonify({"ok": True})

    target = Dispatch.query.get(dispatch_id)
    if not target:
        return jsonify({"ok": False, "error": "Dispatch 不存在"}), 404

    if not move_order_to_dispatch(order, target):
        return jsonify({"ok": False, "error": f"目標車輛已滿（最多 {MAX_CAPACITY} 人）"})

    current = calculate_capacity(target)
    return jsonify({"ok": True, "current": current, "max": MAX_CAPACITY})


# ── 刪除 dispatch ───────────────────────────────────────────────────────────

@dispatch_bp.route("/<int:dispatch_id>/delete", methods=["POST"])
def delete(dispatch_id):
    guard = require_admin()
    if guard:
        return guard

    date     = request.form.get("date", DEPARTURE_OPTIONS[0])
    dispatch = Dispatch.query.get_or_404(dispatch_id)

    # 把所有訂單移回待排車
    for do in dispatch.dispatch_orders:
        if do.order:
            do.order.dispatch_id = None
    db.session.delete(dispatch)
    db.session.commit()

    flash(f"Dispatch #{dispatch_id} 已刪除，訂單已移回待排車。", "success")
    return redirect(url_for("dispatch.index", date=date))
