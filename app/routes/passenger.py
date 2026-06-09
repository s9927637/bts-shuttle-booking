import os
import uuid
import random
import string
from datetime import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for
from app import db
from app.models.order import Order
from app.models.payment import Payment
from app.models.announcement import Announcement

PASSENGER_LIFF_ID = os.environ.get("PASSENGER_LIFF_ID", "")

passenger_bp = Blueprint("passenger", __name__)

PRICE_PER_PERSON   = 2000
DEPOSIT_PER_PERSON = 300
BALANCE_PER_PERSON = 1700

DEPARTURE_OPTIONS = [
    "11/19(四)",
    "11/21(六)",
    "11/22(日)",
]


def _gen_order_no(order_id: int) -> str:
    return f"BTS-KHH-{order_id:06d}"


def _gen_group_id() -> str:
    chars = string.ascii_uppercase + string.digits
    suffix = ''.join(random.choices(chars, k=6))
    return f"BTS-FRIEND-{suffix}"


# ── 首頁 ────────────────────────────────────────────────────────────────────

@passenger_bp.route("/")
def home():
    announcements = (
        Announcement.query
        .filter(Announcement.status == "已發布")
        .order_by(Announcement.is_pinned.desc(), Announcement.created_at.desc())
        .limit(3).all()
    )
    return render_template("passenger/home.html", announcements=announcements)


@passenger_bp.route("/announcements")
def announcement_list():
    page  = max(1, request.args.get("page", 1, type=int))
    per   = 10
    query = (
        Announcement.query
        .filter(Announcement.status == "已發布")
        .order_by(Announcement.is_pinned.desc(), Announcement.created_at.desc())
    )
    total = query.count()
    pages = max(1, (total + per - 1) // per)
    page  = min(page, pages)
    items = query.offset((page - 1) * per).limit(per).all()
    return render_template(
        "passenger/announcements.html",
        announcements=items, total=total, page=page, pages=pages,
        passenger_liff_id=PASSENGER_LIFF_ID,
    )


@passenger_bp.route("/announcements/<int:ann_id>")
def announcement_detail(ann_id):
    a = Announcement.query.get_or_404(ann_id)
    if a.status != "已發布":
        from flask import abort
        abort(404)
    return render_template(
        "passenger/announcement_detail.html",
        announcement=a,
        passenger_liff_id=PASSENGER_LIFF_ID,
    )


@passenger_bp.route("/home-old")
def home_old():
    return render_template("passenger/home_old.html")


@passenger_bp.route("/compare")
def compare():
    return render_template("passenger/compare.html")


# ── 預約表單（舊路由保留相容）────────────────────────────────────────────────

@passenger_bp.route("/book", methods=["GET"])
def book():
    return redirect(url_for("passenger.booking"))


# ── 新預約表單 ───────────────────────────────────────────────────────────────

@passenger_bp.route("/booking", methods=["GET"])
def booking():
    friend_code = request.args.get("friend_code", "").strip() or None
    return render_template("passenger/booking.html",
                           price_per_person=PRICE_PER_PERSON,
                           deposit_per_person=DEPOSIT_PER_PERSON,
                           balance_per_person=BALANCE_PER_PERSON,
                           departure_options=DEPARTURE_OPTIONS,
                           passenger_liff_id=PASSENGER_LIFF_ID,
                           prefill_friend_code=friend_code,
                           form={})


@passenger_bp.route("/booking", methods=["POST"])
def booking_submit():
    form_data = {
        "contact_name":    request.form.get("contact_name", "").strip(),
        "phone":           request.form.get("phone", "").strip(),
        "emergency_phone": request.form.get("emergency_phone", "").strip(),
        "departure_date":  request.form.get("departure_date", "").strip(),
        "passenger_count": request.form.get("passenger_count", "1").strip(),
        "remark":          request.form.get("remark", "").strip(),
    }
    line_user_id = request.form.get("line_user_id", "").strip() or None
    display_name = request.form.get("display_name", "").strip() or None

    try:
        passenger_count = int(form_data["passenger_count"])
        total_amount    = passenger_count * PRICE_PER_PERSON
        deposit_amount  = passenger_count * DEPOSIT_PER_PERSON
        balance_amount  = passenger_count * BALANCE_PER_PERSON

        # 同行群組邏輯
        with_friends = request.form.get("with_friends", "no")
        friend_code  = request.form.get("friend_code", "").strip() or None
        show_group   = None   # None / "created" / "joined"

        if with_friends == "yes":
            if friend_code:
                ref = Order.query.filter_by(group_id=friend_code).first()
                if not ref:
                    raise ValueError("找不到同行群組，請確認同行代碼是否正確。")
                if ref.departure_date != form_data["departure_date"]:
                    raise ValueError("同行代碼對應的出發日期與您選擇的不符。")
                group_id   = friend_code
                show_group = "joined"
            else:
                group_id   = _gen_group_id()
                show_group = "created"
        else:
            group_id = _gen_group_id()

        order = Order(
            order_no        = "TEMP",
            contact_name    = form_data["contact_name"],
            phone           = form_data["phone"],
            emergency_phone = form_data["emergency_phone"] or None,
            departure_date  = form_data["departure_date"],
            passenger_count = passenger_count,
            remark          = form_data["remark"] or None,
            total_amount    = total_amount,
            deposit_amount  = deposit_amount,
            balance_amount  = balance_amount,
            payment_status  = "待付款",
            group_id        = group_id,
            line_user_id    = line_user_id,
            display_name    = display_name,
        )
        db.session.add(order)
        db.session.flush()                       # 取得 id，尚未 commit
        order.order_no = _gen_order_no(order.id)
        db.session.commit()

        flash(f"預約成功！您的訂單編號為 {order.order_no}，請完成訂金匯款後回報。", "success")
        redirect_kwargs = dict(order_no=order.order_no)
        if show_group:
            redirect_kwargs["group_id"]   = order.group_id
            redirect_kwargs["show_group"] = show_group
        return redirect(url_for("passenger.payment_report", **redirect_kwargs))

    except ValueError as e:
        db.session.rollback()
        flash(str(e), "error")
        return render_template("passenger/booking.html",
                               price_per_person=PRICE_PER_PERSON,
                               deposit_per_person=DEPOSIT_PER_PERSON,
                               balance_per_person=BALANCE_PER_PERSON,
                               departure_options=DEPARTURE_OPTIONS,
                               passenger_liff_id=PASSENGER_LIFF_ID,
                               form=form_data)
    except Exception as e:
        db.session.rollback()
        flash(f"預約失敗，請重試。（{e}）", "error")
        return render_template("passenger/booking.html",
                               price_per_person=PRICE_PER_PERSON,
                               deposit_per_person=DEPOSIT_PER_PERSON,
                               balance_per_person=BALANCE_PER_PERSON,
                               departure_options=DEPARTURE_OPTIONS,
                               passenger_liff_id=PASSENGER_LIFF_ID,
                               form=form_data)


# ── 訂單查詢 ────────────────────────────────────────────────────────────────

@passenger_bp.route("/orders/lookup")
def order_lookup():
    return redirect(url_for("passenger.order_search"))


@passenger_bp.route("/orders/search")
def order_search():
    from app.models.vehicle import Vehicle

    line_user_id = request.args.get("line_user_id", "").strip()
    order_no     = request.args.get("order_no", "").strip().upper()
    name         = request.args.get("name", "").strip()
    phone4       = request.args.get("phone4", "").strip()

    orders   = []
    order    = None
    vehicle  = None
    searched = False
    error    = None
    mode     = "form"  # "line" or "form"

    if line_user_id:
        # Priority 1：LINE 身分驗證，直接用 line_user_id 查詢
        mode     = "line"
        searched = True
        orders   = (Order.query
                    .filter_by(line_user_id=line_user_id)
                    .order_by(Order.created_at.desc()).all())

    elif order_no or name or phone4:
        # Priority 2：必須同時提供 訂單編號 + 姓名 + 手機後四碼
        searched = True
        missing = []
        if not order_no:
            missing.append("訂單編號")
        if not name:
            missing.append("姓名")
        if not phone4:
            missing.append("手機後四碼")

        if missing:
            error = f"請填寫：{'、'.join(missing)}"
        elif len(phone4) != 4 or not phone4.isdigit():
            error = "手機後四碼請輸入 4 位數字"
        else:
            order = (Order.query
                     .filter(
                         Order.order_no == order_no,
                         Order.contact_name == name,
                         Order.phone.endswith(phone4),
                     )
                     .first())
            if not order:
                error = "查無符合資料，請確認訂單編號、姓名、手機後四碼是否正確"
            elif order.vehicle_id:
                vehicle = Vehicle.query.get(order.vehicle_id)

    # LINE 模式只有一筆 → 轉為單筆顯示
    if mode == "line" and len(orders) == 1:
        order  = orders[0]
        orders = []
        if order.vehicle_id:
            vehicle = Vehicle.query.get(order.vehicle_id)

    # 群組成員資訊（單筆訂單模式）
    group_member_count = 0
    group_total_pax   = 0
    if order and order.group_id:
        g_orders = Order.query.filter_by(group_id=order.group_id).all()
        group_member_count = len(g_orders)
        group_total_pax   = sum(o.passenger_count for o in g_orders)

    # 重要/緊急公告（顯示於頁面頂部，最多 3 筆）
    important_announcements = (
        Announcement.query
        .filter(
            Announcement.status == "已發布",
            Announcement.announcement_type.in_(["重要公告", "緊急公告"]),
        )
        .order_by(Announcement.is_pinned.desc(), Announcement.created_at.desc())
        .limit(3).all()
    )

    return render_template(
        "passenger/order_search.html",
        order_no=order_no,
        name=name,
        phone4=phone4,
        line_user_id=line_user_id,
        mode=mode,
        order=order,
        orders=orders,
        vehicle=vehicle,
        searched=searched,
        error=error,
        group_member_count=group_member_count,
        group_total_pax=group_total_pax,
        passenger_liff_id=PASSENGER_LIFF_ID,
        important_announcements=important_announcements,
    )


# ── 匯款回報 ────────────────────────────────────────────────────────────────

@passenger_bp.route("/payment/report", methods=["GET"])
def payment_report():
    prefill_order_no = request.args.get("order_no", "")
    line_user_id     = request.args.get("line_user_id", "")
    group_id         = request.args.get("group_id", "")
    show_group       = request.args.get("show_group", "")   # "created" / "joined" / ""
    line_orders = []
    if line_user_id:
        line_orders = Order.query.filter_by(line_user_id=line_user_id)\
                                 .filter(Order.payment_status.in_(["待付款", "待確認"]))\
                                 .order_by(Order.created_at.desc()).all()
    group_orders = []
    if group_id:
        group_orders = Order.query.filter_by(group_id=group_id)\
                                  .order_by(Order.created_at.asc()).all()
    return render_template("passenger/payment_report.html",
                           prefill_order_no=prefill_order_no,
                           line_user_id=line_user_id,
                           line_orders=line_orders,
                           group_id=group_id,
                           group_orders=group_orders,
                           show_group=show_group,
                           passenger_liff_id=PASSENGER_LIFF_ID)


@passenger_bp.route("/payment/report", methods=["POST"])
def payment_report_submit():
    order_no   = request.form.get("order_no", "").strip()
    payer_name = request.form.get("payer_name", "").strip()
    bank_last5 = request.form.get("bank_last5", "").strip()

    if not all([order_no, payer_name, bank_last5]):
        flash("請填寫所有必填欄位。", "error")
        return redirect(url_for("passenger.payment_report", order_no=order_no))

    order = Order.query.filter_by(order_no=order_no).first()
    if not order:
        flash("找不到此訂單編號，請確認後重試。", "error")
        return redirect(url_for("passenger.payment_report"))

    if order.payment_status in ("訂金已確認", "已完成"):
        flash("此訂單已完成訂金確認，無需重複回報。", "error")
        return redirect(url_for("passenger.order_lookup", q=order_no))

    try:
        payment = Payment(
            order_id   = order.id,
            payer_name = payer_name,
            bank_last5 = bank_last5,
            status     = "待確認",
        )
        order.payment_status = "待確認"
        db.session.add(payment)
        db.session.commit()

        flash("匯款資料已送出，我們將盡快確認並通知您。", "success")
        return redirect(url_for("passenger.order_lookup", q=order_no))

    except Exception as e:
        db.session.rollback()
        flash(f"回報失敗，請重試。（{e}）", "error")
        return redirect(url_for("passenger.payment_report", order_no=order_no))


# ── 同行群組邀請連結 ─────────────────────────────────────────────────────────

@passenger_bp.route("/join/<group_id>")
def join_group(group_id):
    group_orders = Order.query.filter_by(group_id=group_id)\
                              .order_by(Order.created_at.asc()).all()
    if not group_orders:
        return render_template("passenger/join_group.html",
                               group_id=group_id, group_orders=[], not_found=True)
    departure_date = group_orders[0].departure_date
    total_pax = sum(o.passenger_count for o in group_orders)
    line_user_id = request.args.get("line_user_id", "")
    return render_template("passenger/join_group.html",
                           group_id=group_id,
                           group_orders=group_orders,
                           departure_date=departure_date,
                           total_pax=total_pax,
                           line_user_id=line_user_id,
                           not_found=False)


@passenger_bp.route("/join/<group_id>", methods=["POST"])
def join_group_submit(group_id):
    order_no = request.form.get("order_no", "").strip()
    group_orders = Order.query.filter_by(group_id=group_id).all()
    if not group_orders:
        flash("找不到同行群組。", "error")
        return redirect(url_for("passenger.join_group", group_id=group_id))

    order = Order.query.filter_by(order_no=order_no).first()
    if not order:
        flash("找不到此訂單編號。", "error")
        return redirect(url_for("passenger.join_group", group_id=group_id))

    if order.group_id == group_id:
        flash("此訂單已在同行群組中。", "error")
        return redirect(url_for("passenger.join_group", group_id=group_id))

    if order.departure_date != group_orders[0].departure_date:
        flash("訂單出發日期與群組不符，無法加入。", "error")
        return redirect(url_for("passenger.join_group", group_id=group_id))

    try:
        order.group_id = group_id
        db.session.commit()
        flash(f"已成功加入同行群組！", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"加入失敗：{e}", "error")

    return redirect(url_for("passenger.join_group", group_id=group_id))
