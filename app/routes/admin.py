import uuid
from datetime import datetime, timedelta
from flask import Blueprint, session, redirect, render_template, request, flash, url_for, jsonify
from werkzeug.security import generate_password_hash
from app import db
from app.models.order import Order
from app.models.vehicle import Vehicle
from app.models.payment import Payment
from app.models.driver import Driver
from app.models.admin import Admin
from app.models.notification import Notification
from app.models.announcement import Announcement
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

    line_bound_passengers   = db.session.query(func.count(Order.id)).filter(Order.line_user_id.isnot(None)).scalar() or 0
    line_unbound_passengers = db.session.query(func.count(Order.id)).filter(Order.line_user_id.is_(None)).scalar() or 0
    line_bound_drivers      = db.session.query(func.count(Driver.id)).filter(Driver.is_line_bound == True).scalar() or 0
    line_unbound_drivers    = db.session.query(func.count(Driver.id)).filter(Driver.is_line_bound == False).scalar() or 0

    now = datetime.utcnow()
    total_announcements = db.session.query(func.count(Announcement.id)).scalar() or 0
    monthly_announcements = db.session.query(func.count(Announcement.id)).filter(
        Announcement.created_at >= now.replace(day=1, hour=0, minute=0, second=0)
    ).scalar() or 0

    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()

    return render_template(
        "admin/dashboard.html",
        stats={
            "total_groups":               total_groups,
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
            "notify_success":             notify_success,
            "notify_failed":             notify_failed,
            "line_bound_passengers":     line_bound_passengers,
            "line_unbound_passengers":   line_unbound_passengers,
            "line_bound_drivers":        line_bound_drivers,
            "line_unbound_drivers":      line_unbound_drivers,
            "total_announcements":        total_announcements,
            "monthly_announcements":      monthly_announcements,
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
        pc           = int(request.form["passenger_count"])
        vehicle_type = request.form.get("vehicle_type", "minibus").strip()
        payment_status = request.form.get("payment_status", "待付款")
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
            payment_status  = payment_status,
            vehicle_type    = vehicle_type,
            vehicle_id      = int(request.form["vehicle_id"]) if request.form.get("vehicle_id") else None,
        )
        db.session.add(order)
        db.session.flush()  # 取得 order.id

        # 若建立時已設為已確認，同步建立 Payment 紀錄
        if payment_status in ("訂金已確認", "已完成"):
            current_admin = Admin.query.get(session.get("admin_id"))
            admin_name = (current_admin.display_name or current_admin.username) if current_admin else "管理員"
            payment = Payment(
                order_id       = order.id,
                payer_name     = order.contact_name,
                payment_source = "admin_confirmed",
                status         = payment_status,
                confirmed_at   = datetime.utcnow(),
                confirmed_by   = admin_name,
                note           = "後台建立訂單時自動建立",
            )
            db.session.add(payment)

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
        old_status = order.payment_status
        order.contact_name    = request.form["contact_name"].strip()
        order.phone           = request.form["phone"].strip()
        order.emergency_phone = request.form.get("emergency_phone", "").strip() or None
        order.departure_date  = request.form["departure_date"].strip()
        order.passenger_count = int(request.form["passenger_count"])
        order.companion_names = request.form.get("companion_names", "").strip() or None
        order.remark          = request.form.get("remark", "").strip() or None
        order.total_amount    = int(request.form["total_amount"])
        new_status            = request.form.get("payment_status", order.payment_status)
        order.payment_status  = new_status
        order.vehicle_type    = request.form.get("vehicle_type", order.vehicle_type or "minibus").strip()
        order.vehicle_id      = int(request.form["vehicle_id"]) if request.form.get("vehicle_id") else None

        # 若付款狀態改為已確認，且該訂單尚無任何 Payment 紀錄，自動建立
        if (new_status in ("訂金已確認", "已完成")
                and new_status != old_status
                and not Payment.query.filter_by(order_id=order.id).first()):
            current_admin = Admin.query.get(session.get("admin_id"))
            admin_name = (current_admin.display_name or current_admin.username) if current_admin else "管理員"
            payment = Payment(
                order_id       = order.id,
                payer_name     = order.contact_name,
                payment_source = "admin_confirmed",
                status         = new_status,
                confirmed_at   = datetime.utcnow(),
                confirmed_by   = admin_name,
                note           = "訂單管理手動確認",
            )
            db.session.add(payment)

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
    source = request.args.get("source", "").strip()
    page   = max(1, request.args.get("page", 1, type=int))

    query = db.session.query(Payment, Order).join(Order, Payment.order_id == Order.id)

    if q:
        query = query.filter(
            db.or_(
                Order.order_no.ilike(f"%{q}%"),
                Order.contact_name.ilike(f"%{q}%"),
                Payment.payer_name.ilike(f"%{q}%"),
                Payment.bank_last5.ilike(f"%{q}%"),
            )
        )
    if status:
        query = query.filter(Payment.status == status)
    if source:
        query = query.filter(Payment.payment_source == source)

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
        current_admin = Admin.query.get(session.get("admin_id"))
        admin_name = (current_admin.display_name or current_admin.username) if current_admin else "管理員"
        payment.status = new_status
        if new_status == "訂金已確認":
            payment.confirmed_at = datetime.utcnow()
            payment.confirmed_by = admin_name
            payment.payment_source = "admin_confirmed"
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


@admin_bp.route("/api/order-lookup")
def api_order_lookup():
    guard = require_admin()
    if guard:
        return jsonify({"found": False})
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"found": False})
    order = Order.query.filter(
        db.or_(Order.order_no.ilike(f"%{q}%"), Order.contact_name.ilike(f"%{q}%"))
    ).first()
    if order:
        return jsonify({
            "found": True,
            "id": order.id,
            "order_no": order.order_no,
            "contact_name": order.contact_name,
            "departure_date": order.departure_date,
            "passenger_count": order.passenger_count,
        })
    return jsonify({"found": False})


@admin_bp.route("/payments/create", methods=["POST"])
def payment_create():
    guard = require_admin()
    if guard:
        return guard

    order_id = request.form.get("order_id", type=int)
    order = Order.query.get(order_id) if order_id else None
    if not order:
        flash("找不到訂單", "error")
        return redirect(url_for("admin.payments"))

    try:
        current_admin = Admin.query.get(session.get("admin_id"))
        admin_name = (current_admin.display_name or current_admin.username) if current_admin else "管理員"
        source = request.form.get("payment_source", "admin_confirmed").strip()
        status = request.form.get("status", "訂金已確認").strip()
        amount_raw = request.form.get("amount", "").strip()
        amount = int(amount_raw) if amount_raw else None
        note = request.form.get("note", "").strip() or None

        payment = Payment(
            order_id       = order_id,
            payer_name     = order.contact_name,
            payment_source = source,
            amount         = amount,
            status         = status,
            note           = note,
        )
        if status == "訂金已確認":
            payment.confirmed_at = datetime.utcnow()
            payment.confirmed_by = admin_name
            order.payment_status = "訂金已確認"

        db.session.add(payment)
        db.session.commit()
        flash(f"付款紀錄已新增（訂單 {order.order_no}）", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"新增失敗：{e}", "error")

    return redirect(url_for("admin.payments"))


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


# ── Announcements ──────────────────────────────────────────────────────────

ANNOUNCEMENT_TYPES = ["一般公告", "重要公告", "緊急公告"]
ANNOUNCEMENT_STATUSES = ["草稿", "已發布", "已下架"]
LINE_TARGETS = ["全部乘客", "11/19 乘客", "11/21 乘客", "11/22 乘客", "全部司機"]


@admin_bp.route("/announcements")
def announcements():
    guard = require_admin()
    if guard:
        return guard

    page  = max(1, request.args.get("page", 1, type=int))
    query = Announcement.query.order_by(Announcement.is_pinned.desc(), Announcement.created_at.desc())
    total = query.count()
    pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page  = min(page, pages)
    items = query.offset((page - 1) * PER_PAGE).limit(PER_PAGE).all()

    return render_template(
        "admin/announcements.html",
        announcements=items,
        total=total, page=page, pages=pages,
        announcement_types=ANNOUNCEMENT_TYPES,
        announcement_statuses=ANNOUNCEMENT_STATUSES,
        line_targets=LINE_TARGETS,
    )


@admin_bp.route("/announcements/create", methods=["POST"])
def announcement_create():
    guard = require_admin()
    if guard:
        return guard

    try:
        a = Announcement(
            title             = request.form["title"].strip(),
            content           = request.form["content"].strip(),
            announcement_type = request.form.get("announcement_type", "一般公告"),
            status            = request.form.get("status", "草稿"),
            is_pinned         = bool(request.form.get("is_pinned")),
            publish_to_line   = bool(request.form.get("publish_to_line")),
            line_target       = request.form.get("line_target") or None,
        )
        db.session.add(a)
        db.session.flush()

        if a.status == "已發布" and a.publish_to_line:
            from app.services.line_service import send_announcement_notification
            send_announcement_notification(a)

        db.session.commit()
        flash("公告已建立。", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"建立失敗：{e}", "error")

    return redirect(url_for("admin.announcements"))


@admin_bp.route("/announcements/<int:ann_id>/update", methods=["POST"])
def announcement_update(ann_id):
    guard = require_admin()
    if guard:
        return guard

    a = Announcement.query.get_or_404(ann_id)
    old_status = a.status
    try:
        a.title             = request.form["title"].strip()
        a.content           = request.form["content"].strip()
        a.announcement_type = request.form.get("announcement_type", a.announcement_type)
        a.status            = request.form.get("status", a.status)
        a.is_pinned         = bool(request.form.get("is_pinned"))
        a.publish_to_line   = bool(request.form.get("publish_to_line"))
        a.line_target       = request.form.get("line_target") or None
        a.updated_at        = datetime.utcnow()

        if a.status == "已發布" and old_status != "已發布" and a.publish_to_line:
            from app.services.line_service import send_announcement_notification
            send_announcement_notification(a)

        db.session.commit()
        flash("公告已更新。", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"更新失敗：{e}", "error")

    return redirect(url_for("admin.announcements"))


@admin_bp.route("/announcements/<int:ann_id>/delete", methods=["POST"])
def announcement_delete(ann_id):
    guard = require_admin()
    if guard:
        return guard

    a = Announcement.query.get_or_404(ann_id)
    try:
        db.session.delete(a)
        db.session.commit()
        flash("公告已刪除。", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"刪除失敗：{e}", "error")

    return redirect(url_for("admin.announcements"))


# ── Notifications Log ──────────────────────────────────────────────────────

@admin_bp.route("/notifications")
def notifications_log():
    guard = require_admin()
    if guard:
        return guard

    page  = max(1, request.args.get("page", 1, type=int))
    query = Notification.query.order_by(Notification.created_at.desc())
    total = query.count()
    pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page  = min(page, pages)
    items = query.offset((page - 1) * PER_PAGE).limit(PER_PAGE).all()

    return render_template(
        "admin/notifications.html",
        notifications=items,
        total=total, page=page, pages=pages,
    )


@admin_bp.route("/notifications/<int:notif_id>/resend", methods=["POST"])
def notification_resend(notif_id):
    guard = require_admin()
    if guard:
        return guard

    from app.services.line_service import resend_notification
    result = resend_notification(notif_id)
    if result["status"] == "success":
        flash("已重新發送。", "success")
    else:
        flash(f"發送失敗：{result.get('msg', '')}", "error")

    return redirect(url_for("admin.notifications_log"))


# ── Revenue ────────────────────────────────────────────────────────────────

def _revenue_stats():
    """Calculate all revenue stats via aggregate queries. No per-row loops."""
    ACTIVE = ["待付款", "待確認", "訂金已確認", "已完成"]

    # ── 總覽 ───────────────────────────────────────────────────────────────
    total_revenue = db.session.query(
        func.coalesce(func.sum(Order.total_amount), 0)
    ).filter(Order.payment_status.in_(ACTIVE)).scalar()

    collected = (
        db.session.query(func.coalesce(func.sum(Order.deposit_amount), 0))
        .filter(Order.payment_status == "訂金已確認").scalar()
        +
        db.session.query(func.coalesce(func.sum(Order.total_amount), 0))
        .filter(Order.payment_status == "已完成").scalar()
    )

    pending_revenue = total_revenue - collected

    total_pax = db.session.query(
        func.coalesce(func.sum(Order.passenger_count), 0)
    ).filter(Order.payment_status.in_(ACTIVE)).scalar()

    # ── 場次營收 ───────────────────────────────────────────────────────────
    session_rows = db.session.query(
        Order.departure_date,
        func.sum(Order.passenger_count).label("pax"),
        func.sum(Order.total_amount).label("revenue"),
    ).filter(Order.payment_status.in_(ACTIVE)).group_by(Order.departure_date).all()

    sessions = []
    for row in sorted(session_rows, key=lambda r: r.departure_date):
        dep = row.departure_date
        rev = row.revenue or 0
        pax = row.pax or 0
        # 已收 for this date
        c1 = db.session.query(func.coalesce(func.sum(Order.deposit_amount), 0)).filter(
            Order.payment_status == "訂金已確認", Order.departure_date == dep).scalar()
        c2 = db.session.query(func.coalesce(func.sum(Order.total_amount), 0)).filter(
            Order.payment_status == "已完成", Order.departure_date == dep).scalar()
        col = c1 + c2
        rate = round(col / rev * 100) if rev > 0 else 0
        sessions.append({
            "date": dep, "pax": pax, "revenue": rev,
            "collected": col, "pending": rev - col, "rate": rate,
        })

    # ── 收款狀態 ───────────────────────────────────────────────────────────
    cnt_done     = db.session.query(func.count(Order.id)).filter(Order.payment_status == "已完成").scalar() or 0
    cnt_deposit  = db.session.query(func.count(Order.id)).filter(Order.payment_status == "訂金已確認").scalar() or 0
    cnt_unpaid   = db.session.query(func.count(Order.id)).filter(
        Order.payment_status.in_(["待付款", "待確認"])).scalar() or 0
    cnt_total    = cnt_done + cnt_deposit + cnt_unpaid or 1   # avoid div/0

    pct_done    = round(cnt_done    / cnt_total * 100)
    pct_deposit = round(cnt_deposit / cnt_total * 100)
    pct_unpaid  = 100 - pct_done - pct_deposit

    # ── 待收尾款 ───────────────────────────────────────────────────────────
    unpaid_orders = (
        Order.query
        .filter(Order.payment_status.in_(["待付款", "待確認", "訂金已確認"]))
        .order_by(Order.created_at.desc())
        .all()
    )
    pending_rows = []
    for o in unpaid_orders:
        if o.payment_status == "訂金已確認":
            owed = o.balance_amount
        else:
            owed = o.total_amount
        pending_rows.append({"order": o, "owed": owed})

    pending_total = sum(r["owed"] for r in pending_rows)

    # ── 車型營收排行 ───────────────────────────────────────────────────────
    type_rows = db.session.query(
        Order.vehicle_type,
        func.count(Order.id).label("orders"),
        func.sum(Order.passenger_count).label("pax"),
        func.sum(Order.total_amount).label("revenue"),
    ).filter(Order.payment_status.in_(ACTIVE)).group_by(Order.vehicle_type).all()

    vehicle_stats = sorted(
        [{"type": r.vehicle_type, "orders": r.orders, "pax": r.pax or 0, "revenue": r.revenue or 0}
         for r in type_rows],
        key=lambda x: x["revenue"], reverse=True,
    )

    # ── 車輛使用 ───────────────────────────────────────────────────────────
    dispatched = db.session.query(func.count(Order.id)).filter(
        Order.vehicle_id.isnot(None),
        Order.payment_status.in_(["訂金已確認", "已完成"])
    ).scalar() or 0
    undispatched = db.session.query(func.count(Order.id)).filter(
        Order.vehicle_id.is_(None),
        Order.payment_status.in_(["訂金已確認", "已完成"])
    ).scalar() or 0

    return {
        "total_revenue": total_revenue,
        "collected": collected,
        "pending_revenue": pending_revenue,
        "total_pax": total_pax,
        "sessions": sessions,
        "cnt_done": cnt_done, "cnt_deposit": cnt_deposit, "cnt_unpaid": cnt_unpaid,
        "pct_done": pct_done, "pct_deposit": pct_deposit, "pct_unpaid": pct_unpaid,
        "pending_rows": pending_rows,
        "pending_total": pending_total,
        "vehicle_stats": vehicle_stats,
        "dispatched": dispatched,
        "undispatched": undispatched,
    }


@admin_bp.route("/revenue")
def revenue():
    guard = require_admin()
    if guard:
        return guard
    stats = _revenue_stats()
    return render_template("admin/revenue.html", **stats)


@admin_bp.route("/revenue/export/csv")
def revenue_export_csv():
    guard = require_admin()
    if guard:
        return guard
    import csv, io
    from flask import Response
    orders = Order.query.filter(
        Order.payment_status.in_(["待付款", "待確認", "訂金已確認", "已完成"])
    ).order_by(Order.departure_date, Order.created_at).all()

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["訂單編號", "姓名", "電話", "場次", "乘客數", "總金額", "已付款", "未付款", "付款狀態", "車型"])
    for o in orders:
        if o.payment_status == "已完成":
            paid = o.total_amount; owed = 0
        elif o.payment_status == "訂金已確認":
            paid = o.deposit_amount; owed = o.balance_amount
        else:
            paid = 0; owed = o.total_amount
        w.writerow([o.order_no, o.contact_name, o.phone, o.departure_date,
                    o.passenger_count, o.total_amount, paid, owed, o.payment_status,
                    "NX200 包車" if o.vehicle_type == "nx200" else "九座商旅車"])

    fname = f"BTS營收報表_{datetime.utcnow().strftime('%Y-%m-%d')}.csv"
    buf.seek(0)
    return Response(
        buf.getvalue().encode("utf-8-sig"),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{fname}"}
    )


@admin_bp.route("/revenue/export/xlsx")
def revenue_export_xlsx():
    guard = require_admin()
    if guard:
        return guard
    import io
    from flask import Response
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    except ImportError:
        flash("需要安裝 openpyxl：pip install openpyxl", "error")
        return redirect(url_for("admin.revenue"))

    orders = Order.query.filter(
        Order.payment_status.in_(["待付款", "待確認", "訂金已確認", "已完成"])
    ).order_by(Order.departure_date, Order.created_at).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "營收報表"

    header_fill = PatternFill("solid", fgColor="111827")
    header_font = Font(color="FFFFFF", bold=True, size=10)
    thin = Side(style="thin", color="E5E7EB")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    headers = ["訂單編號", "姓名", "電話", "場次", "乘客數", "總金額", "已付款", "未付款", "付款狀態", "車型"]
    col_widths = [22, 12, 14, 16, 8, 12, 12, 12, 12, 14]

    for ci, (h, w) in enumerate(zip(headers, col_widths), start=1):
        cell = ws.cell(row=1, column=ci, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border
        ws.column_dimensions[ws.cell(row=1, column=ci).column_letter].width = w

    ws.row_dimensions[1].height = 20

    for ri, o in enumerate(orders, start=2):
        if o.payment_status == "已完成":
            paid = o.total_amount; owed = 0
        elif o.payment_status == "訂金已確認":
            paid = o.deposit_amount; owed = o.balance_amount
        else:
            paid = 0; owed = o.total_amount
        row_data = [
            o.order_no, o.contact_name, o.phone, o.departure_date,
            o.passenger_count, o.total_amount, paid, owed, o.payment_status,
            "NX200 包車" if o.vehicle_type == "nx200" else "九座商旅車"
        ]
        for ci, val in enumerate(row_data, start=1):
            cell = ws.cell(row=ri, column=ci, value=val)
            cell.border = border
            cell.alignment = Alignment(vertical="center")
            if ci in (6, 7, 8):
                cell.number_format = '#,##0'

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    fname = f"BTS營收報表_{datetime.utcnow().strftime('%Y-%m-%d')}.xlsx"
    return Response(
        buf.getvalue(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{fname}"}
    )


@admin_bp.route("/revenue/export/unpaid-xlsx")
def revenue_export_unpaid_xlsx():
    guard = require_admin()
    if guard:
        return guard
    import io
    from flask import Response
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    except ImportError:
        flash("需要安裝 openpyxl", "error")
        return redirect(url_for("admin.revenue"))

    orders = Order.query.filter(
        Order.payment_status.in_(["待付款", "待確認", "訂金已確認"])
    ).order_by(Order.departure_date, Order.created_at).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "未付款名單"

    header_fill = PatternFill("solid", fgColor="7C3AED")
    header_font = Font(color="FFFFFF", bold=True, size=10)
    thin = Side(style="thin", color="E5E7EB")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    headers = ["訂單編號", "姓名", "電話", "場次", "車型", "乘客數", "總金額", "已付款", "未付款", "付款狀態"]
    col_widths = [22, 12, 14, 16, 14, 8, 12, 12, 12, 12]
    for ci, (h, w) in enumerate(zip(headers, col_widths), start=1):
        cell = ws.cell(row=1, column=ci, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border
        ws.column_dimensions[ws.cell(row=1, column=ci).column_letter].width = w
    ws.row_dimensions[1].height = 20

    for ri, o in enumerate(orders, start=2):
        paid = o.deposit_amount if o.payment_status == "訂金已確認" else 0
        owed = o.balance_amount if o.payment_status == "訂金已確認" else o.total_amount
        row_data = [
            o.order_no, o.contact_name, o.phone, o.departure_date,
            "NX200 包車" if o.vehicle_type == "nx200" else "九座商旅車",
            o.passenger_count, o.total_amount, paid, owed, o.payment_status
        ]
        for ci, val in enumerate(row_data, start=1):
            cell = ws.cell(row=ri, column=ci, value=val)
            cell.border = border
            cell.alignment = Alignment(vertical="center")
            if ci in (7, 8, 9):
                cell.number_format = '#,##0'

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    fname = f"BTS未付款名單_{datetime.utcnow().strftime('%Y-%m-%d')}.xlsx"
    return Response(
        buf.getvalue(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{fname}"}
    )


@admin_bp.route("/revenue/print")
def revenue_print():
    guard = require_admin()
    if guard:
        return guard
    orders = Order.query.filter(
        Order.payment_status.in_(["訂金已確認", "已完成"])
    ).order_by(Order.departure_date, Order.contact_name).all()
    return render_template("admin/revenue_print.html", orders=orders, now=datetime.utcnow())
