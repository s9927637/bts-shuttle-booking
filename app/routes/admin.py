import uuid
from datetime import datetime, timedelta
from flask import Blueprint, session, redirect, render_template, request, flash, url_for
from werkzeug.security import generate_password_hash
from app import db
from app.models.order import Order
from app.models.vehicle import Vehicle
from app.models.payment import Payment
from app.models.driver import Driver
from app.models.admin import Admin
from app.models.notification import Notification
from sqlalchemy import func

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

PER_PAGE = 20

PAYMENT_STATUSES = ["待付款", "待確認", "訂金已確認", "已完成"]
PRICE_PER_PERSON = 2000

DEPARTURE_OPTIONS = [
    "11/19(四)",
    "11/21(六)",
    "11/22(日)",
]


def require_admin():
    if not session.get("admin_id"):
        return redirect(url_for("auth.login_page"))


def _gen_order_no():
    prefix = datetime.utcnow().strftime("%Y%m%d")
    suffix = uuid.uuid4().hex[:6].upper()
    return f"BTS-{prefix}-{suffix}"


# ── Dashboard ──────────────────────────────────────────────────────────────

@admin_bp.route("/")
def dashboard():
    guard = require_admin()
    if guard:
        return guard

    total_groups      = db.session.query(func.count(func.distinct(Order.group_id))).filter(Order.group_id.isnot(None)).scalar() or 0
    total_orders      = db.session.query(func.count(Order.id)).scalar() or 0
    total_passengers  = db.session.query(func.sum(Order.passenger_count)).scalar() or 0
    unpaid_orders     = db.session.query(func.count(Order.id)).filter(Order.payment_status == "待付款").scalar() or 0
    pending_orders    = db.session.query(func.count(Order.id)).filter(Order.payment_status == "待確認").scalar() or 0
    confirmed_orders  = db.session.query(func.count(Order.id)).filter(Order.payment_status == "訂金已確認").scalar() or 0
    completed_orders  = db.session.query(func.count(Order.id)).filter(Order.payment_status == "已完成").scalar() or 0
    dispatched_orders = db.session.query(func.count(Order.id)).filter(
        Order.payment_status == "訂金已確認", Order.dispatch_id.isnot(None)
    ).scalar() or 0
    total_revenue     = db.session.query(func.sum(Order.total_amount)).filter(
        Order.payment_status.in_(["訂金已確認", "已完成"])
    ).scalar() or 0
    total_deposit_collected = db.session.query(func.sum(Order.deposit_amount)).filter(
        Order.payment_status.in_(["訂金已確認", "已完成"])
    ).scalar() or 0
    total_balance_pending = db.session.query(func.sum(Order.balance_amount)).filter(
        Order.payment_status == "訂金已確認"
    ).scalar() or 0

    notify_success = db.session.query(func.count(Notification.id)).filter(Notification.status == "success").scalar() or 0
    notify_failed  = db.session.query(func.count(Notification.id)).filter(Notification.status == "failed").scalar() or 0

    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()

    return render_template(
        "admin/dashboard.html",
        stats={
            "total_groups":             total_groups,
            "total_orders":             total_orders,
            "total_passengers":         total_passengers,
            "unpaid_orders":            unpaid_orders,
            "pending_orders":           pending_orders,
            "confirmed_orders":         confirmed_orders,
            "completed_orders":         completed_orders,
            "dispatched_orders":        dispatched_orders,
            "total_revenue":            total_revenue,
            "total_deposit_collected":  total_deposit_collected,
            "total_balance_pending":    total_balance_pending,
            "notify_success":           notify_success,
            "notify_failed":            notify_failed,
        },
        recent_orders=recent_orders,
    )


# ── Orders list ────────────────────────────────────────────────────────────

@admin_bp.route("/orders")
def orders():
    guard = require_admin()
    if guard:
        return guard

    q      = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    page   = max(1, request.args.get("page", 1, type=int))

    query = Order.query
    if q:
        query = query.filter(
            db.or_(
                Order.contact_name.ilike(f"%{q}%"),
                Order.order_no.ilike(f"%{q}%"),
                Order.phone.ilike(f"%{q}%"),
            )
        )
    if status:
        query = query.filter(Order.payment_status == status)

    total  = query.count()
    pages  = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page   = min(page, pages)

    orders_list = (
        query.order_by(Order.created_at.desc())
        .offset((page - 1) * PER_PAGE)
        .limit(PER_PAGE)
        .all()
    )
    vehicles = Vehicle.query.order_by(Vehicle.plate_number).all()

    return render_template(
        "admin/orders.html",
        orders=orders_list,
        total=total,
        page=page,
        pages=pages,
        payment_statuses=PAYMENT_STATUSES,
        departure_options=DEPARTURE_OPTIONS,
        price_per_person=PRICE_PER_PERSON,
        vehicles=vehicles,
    )


# ── Create ─────────────────────────────────────────────────────────────────

@admin_bp.route("/orders/create", methods=["POST"])
def order_create():
    guard = require_admin()
    if guard:
        return guard

    try:
        pc = int(request.form["passenger_count"])
        order = Order(
            order_no        = _gen_order_no(),
            contact_name    = request.form["contact_name"].strip(),
            phone           = request.form["phone"].strip(),
            emergency_phone = request.form.get("emergency_phone", "").strip() or None,
            departure_date  = request.form["departure_date"].strip(),
            passenger_count = pc,
            companion_names = request.form.get("companion_names", "").strip() or None,
            remark          = request.form.get("remark", "").strip() or None,
            total_amount    = pc * 2000,
            deposit_amount  = pc * 300,
            balance_amount  = pc * 1700,
            payment_status  = request.form.get("payment_status", "待付款"),
            vehicle_id      = int(request.form["vehicle_id"]) if request.form.get("vehicle_id") else None,
        )
        db.session.add(order)
        db.session.commit()
        flash("訂單已新增", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"新增失敗：{e}", "error")

    return redirect(url_for("admin.orders"))


# ── Edit ───────────────────────────────────────────────────────────────────

@admin_bp.route("/orders/<int:order_id>/edit", methods=["POST"])
def order_edit(order_id):
    guard = require_admin()
    if guard:
        return guard

    order = Order.query.get_or_404(order_id)
    try:
        order.contact_name    = request.form["contact_name"].strip()
        order.phone           = request.form["phone"].strip()
        order.emergency_phone = request.form.get("emergency_phone", "").strip() or None
        order.departure_date  = request.form["departure_date"].strip()
        order.passenger_count = int(request.form["passenger_count"])
        order.companion_names = request.form.get("companion_names", "").strip() or None
        order.remark          = request.form.get("remark", "").strip() or None
        order.total_amount    = int(request.form["total_amount"])
        order.payment_status  = request.form.get("payment_status", order.payment_status)
        order.vehicle_id      = int(request.form["vehicle_id"]) if request.form.get("vehicle_id") else None

        db.session.commit()
        flash("訂單已更新", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"更新失敗：{e}", "error")

    return redirect(url_for("admin.orders",
                            q=request.args.get("q", ""),
                            status=request.args.get("status", ""),
                            page=request.args.get("page", 1)))


# ── Delete ─────────────────────────────────────────────────────────────────

@admin_bp.route("/orders/<int:order_id>/delete", methods=["POST"])
def order_delete(order_id):
    guard = require_admin()
    if guard:
        return guard

    order = Order.query.get_or_404(order_id)
    try:
        Payment.query.filter_by(order_id=order_id).delete()
        db.session.delete(order)
        db.session.commit()
        flash("訂單已刪除", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"刪除失敗：{e}", "error")

    return redirect(url_for("admin.orders"))


# ── Payments list ──────────────────────────────────────────────────────────

PAYMENT_RECORD_STATUSES = ["待確認", "訂金已確認", "已退款"]


@admin_bp.route("/payments")
def payments():
    guard = require_admin()
    if guard:
        return guard

    q      = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    page   = max(1, request.args.get("page", 1, type=int))

    query = db.session.query(Payment, Order).join(Order, Payment.order_id == Order.id)

    if q:
        query = query.filter(
            db.or_(
                Order.order_no.ilike(f"%{q}%"),
                Payment.payer_name.ilike(f"%{q}%"),
                Payment.bank_last5.ilike(f"%{q}%"),
            )
        )
    if status:
        query = query.filter(Payment.status == status)

    total  = query.count()
    pages  = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page   = min(page, pages)

    rows = (
        query.order_by(Payment.created_at.desc())
        .offset((page - 1) * PER_PAGE)
        .limit(PER_PAGE)
        .all()
    )

    return render_template(
        "admin/payments.html",
        rows=rows,
        total=total,
        page=page,
        pages=pages,
        statuses=PAYMENT_RECORD_STATUSES,
    )


@admin_bp.route("/payments/<int:payment_id>/status", methods=["POST"])
def payment_update_status(payment_id):
    guard = require_admin()
    if guard:
        return guard

    payment = Payment.query.get_or_404(payment_id)
    new_status = request.form.get("status", "").strip()

    if new_status not in PAYMENT_RECORD_STATUSES:
        flash("無效的狀態", "error")
        return redirect(url_for("admin.payments"))

    try:
        payment.status = new_status
        if new_status == "訂金已確認":
            order = Order.query.get(payment.order_id)
            if order:
                order.payment_status = "訂金已確認"
        db.session.commit()
        flash("付款狀態已更新", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"更新失敗：{e}", "error")

    return redirect(url_for("admin.payments",
                            q=request.args.get("q", ""),
                            status=request.args.get("status", ""),
                            page=request.args.get("page", 1)))


# ── Vehicles ───────────────────────────────────────────────────────────────

@admin_bp.route("/vehicles")
def vehicles():
    guard = require_admin()
    if guard:
        return guard

    q     = request.args.get("q", "").strip()
    query = Vehicle.query
    if q:
        query = query.filter(
            db.or_(
                Vehicle.plate_number.ilike(f"%{q}%"),
                Vehicle.driver_name.ilike(f"%{q}%"),
                Vehicle.driver_phone.ilike(f"%{q}%"),
            )
        )

    vehicles_list = query.order_by(Vehicle.plate_number).all()
    return render_template("admin/vehicles.html", vehicles=vehicles_list, total=len(vehicles_list))


@admin_bp.route("/vehicles/create", methods=["POST"])
def vehicle_create():
    guard = require_admin()
    if guard:
        return guard

    try:
        v = Vehicle(
            plate_number = request.form["plate_number"].strip(),
            driver_name  = request.form["driver_name"].strip(),
            driver_phone = request.form["driver_phone"].strip(),
            seat_limit   = int(request.form.get("seat_limit", 8)),
        )
        db.session.add(v)
        db.session.commit()
        flash("車輛已新增", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"新增失敗：{e}", "error")

    return redirect(url_for("admin.vehicles"))


@admin_bp.route("/vehicles/<int:vehicle_id>/edit", methods=["POST"])
def vehicle_edit(vehicle_id):
    guard = require_admin()
    if guard:
        return guard

    v = Vehicle.query.get_or_404(vehicle_id)
    try:
        v.plate_number = request.form["plate_number"].strip()
        v.driver_name  = request.form["driver_name"].strip()
        v.driver_phone = request.form["driver_phone"].strip()
        v.seat_limit   = int(request.form.get("seat_limit", v.seat_limit))
        db.session.commit()
        flash("車輛已更新", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"更新失敗：{e}", "error")

    return redirect(url_for("admin.vehicles", q=request.args.get("q", "")))


@admin_bp.route("/vehicles/<int:vehicle_id>/delete", methods=["POST"])
def vehicle_delete(vehicle_id):
    guard = require_admin()
    if guard:
        return guard

    v = Vehicle.query.get_or_404(vehicle_id)
    try:
        db.session.delete(v)
        db.session.commit()
        flash("車輛已刪除", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"刪除失敗：{e}", "error")

    return redirect(url_for("admin.vehicles"))


# ── Drivers ────────────────────────────────────────────────────────────────

BIND_STATUSES = ["未綁定", "已綁定"]


@admin_bp.route("/drivers")
def drivers():
    guard = require_admin()
    if guard:
        return guard

    q     = request.args.get("q", "").strip()
    query = Driver.query
    if q:
        query = query.filter(
            db.or_(
                Driver.name.ilike(f"%{q}%"),
                Driver.phone.ilike(f"%{q}%"),
                Driver.line_user_id.ilike(f"%{q}%"),
            )
        )

    drivers_list = query.order_by(Driver.name).all()
    return render_template("admin/drivers.html",
                           drivers=drivers_list,
                           total=len(drivers_list),
                           bind_statuses=BIND_STATUSES)


@admin_bp.route("/drivers/create", methods=["POST"])
def driver_create():
    guard = require_admin()
    if guard:
        return guard

    try:
        d = Driver(
            name         = request.form["name"].strip(),
            phone        = request.form["phone"].strip(),
            line_user_id = request.form.get("line_user_id", "").strip() or None,
            bind_status  = request.form.get("bind_status", "未綁定"),
        )
        db.session.add(d)
        db.session.commit()
        flash("司機已新增", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"新增失敗：{e}", "error")

    return redirect(url_for("admin.drivers"))


@admin_bp.route("/drivers/<int:driver_id>/edit", methods=["POST"])
def driver_edit(driver_id):
    guard = require_admin()
    if guard:
        return guard

    d = Driver.query.get_or_404(driver_id)
    try:
        d.name         = request.form["name"].strip()
        d.phone        = request.form["phone"].strip()
        d.line_user_id = request.form.get("line_user_id", "").strip() or None
        d.bind_status  = request.form.get("bind_status", d.bind_status)
        db.session.commit()
        flash("司機資料已更新", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"更新失敗：{e}", "error")

    return redirect(url_for("admin.drivers", q=request.args.get("q", "")))


@admin_bp.route("/drivers/<int:driver_id>/delete", methods=["POST"])
def driver_delete(driver_id):
    guard = require_admin()
    if guard:
        return guard

    d = Driver.query.get_or_404(driver_id)
    try:
        db.session.delete(d)
        db.session.commit()
        flash("司機已刪除", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"刪除失敗：{e}", "error")

    return redirect(url_for("admin.drivers"))


# ── 管理員帳號管理 ──────────────────────────────────────────────────────────

@admin_bp.route("/admins")
def admins():
    guard = require_admin()
    if guard:
        return guard

    admin_list = Admin.query.order_by(Admin.created_at.asc()).all()
    current_id = session.get("admin_id")
    return render_template("admin/admins.html", admin_list=admin_list, current_id=current_id)


@admin_bp.route("/admins/create", methods=["POST"])
def admin_create():
    guard = require_admin()
    if guard:
        return guard

    username     = request.form.get("username", "").strip()
    password     = request.form.get("password", "").strip()
    display_name = request.form.get("display_name", "").strip()

    if not username or not password:
        flash("帳號與密碼為必填。", "error")
        return redirect(url_for("admin.admins"))

    if Admin.query.filter_by(username=username).first():
        flash(f"帳號「{username}」已存在。", "error")
        return redirect(url_for("admin.admins"))

    try:
        a = Admin(username=username, password_hash=generate_password_hash(password), display_name=display_name or None)
        db.session.add(a)
        db.session.commit()
        flash(f"管理員「{username}」已建立。", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"建立失敗：{e}", "error")

    return redirect(url_for("admin.admins"))


@admin_bp.route("/admins/<int:admin_id>/update", methods=["POST"])
def admin_update(admin_id):
    guard = require_admin()
    if guard:
        return guard

    a = Admin.query.get_or_404(admin_id)
    display_name = request.form.get("display_name", "").strip()
    password     = request.form.get("password", "").strip()

    try:
        a.display_name = display_name or None
        if password:
            a.password_hash = generate_password_hash(password)
        db.session.commit()
        flash(f"管理員「{a.username}」已更新。", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"更新失敗：{e}", "error")

    return redirect(url_for("admin.admins"))


@admin_bp.route("/admins/<int:admin_id>/delete", methods=["POST"])
def admin_delete(admin_id):
    guard = require_admin()
    if guard:
        return guard

    current_id = session.get("admin_id")
    if admin_id == current_id:
        flash("無法刪除目前登入的帳號。", "error")
        return redirect(url_for("admin.admins"))

    a = Admin.query.get_or_404(admin_id)
    try:
        db.session.delete(a)
        db.session.commit()
        flash(f"管理員「{a.username}」已刪除。", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"刪除失敗：{e}", "error")

    return redirect(url_for("admin.admins"))
