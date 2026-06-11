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

# NX200 固定定價（1 台，固定 4 人）
NX200_PAX     = 4
NX200_TOTAL   = 10000
NX200_DEPOSIT = 1200
NX200_BALANCE = 8800
NX200_QUOTA   = 1   # 全程只允許 1 台


def _nx200_available() -> bool:
    """NX200 尚有名額（未被任何非取消訂單佔用）"""
    count = Order.query.filter(
        Order.vehicle_type == "nx200",
        Order.payment_status != "已取消"
    ).count()
    return count < NX200_QUOTA

DEPARTURE_OPTIONS = [
    {"value": "11/19(四)", "label": "11/19（四） 已額滿", "disabled": True},
    {"value": "11/21(六)", "label": "11/21（六） 已額滿", "disabled": True},
    {"value": "11/22(日)", "label": "11/22（日）",       "disabled": False},
]
AVAILABLE_DATES = {opt["value"] for opt in DEPARTURE_OPTIONS if not opt["disabled"]}


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
                           nx200_pax=NX200_PAX,
                           nx200_total=NX200_TOTAL,
                           nx200_deposit=NX200_DEPOSIT,
                           nx200_balance=NX200_BALANCE,
                           nx200_available=_nx200_available(),
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

    vehicle_type = request.form.get("vehicle_type", "minibus").strip()

    try:
        # 後端驗證：禁止提交已額滿場次（即使前端 HTML 被修改）
        dep = form_data["departure_date"]
        if dep not in AVAILABLE_DATES:
            raise ValueError("所選場次目前不開放預約，請選擇 11/22（日）場次。")

        # 車輛方案計價
        if vehicle_type == "nx200":
            if not _nx200_available():
                raise ValueError("NX200 專屬包車已售完，請選擇九座商旅車方案。")
            passenger_count = NX200_PAX
            total_amount    = NX200_TOTAL
            deposit_amount  = NX200_DEPOSIT
            balance_amount  = NX200_BALANCE
        else:
            vehicle_type    = "minibus"
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
            vehicle_type    = vehicle_type,
            group_id        = group_id,
            line_user_id    = line_user_id,
            display_name    = display_name,
        )
        db.session.add(order)
        db.session.flush()                       # 取得 id，尚未 commit
        order.order_no = _gen_order_no(order.id)
        db.session.commit()

        return redirect(url_for("passenger.order_detail",
                                order_no=order.order_no, new=1))

    except (ValueError, Exception) as e:
        db.session.rollback()
        msg = str(e) if isinstance(e, ValueError) else f"預約失敗，請重試。（{e}）"
        flash(msg, "error")
        return render_template("passenger/booking.html",
                               price_per_person=PRICE_PER_PERSON,
                               deposit_per_person=DEPOSIT_PER_PERSON,
                               balance_per_person=BALANCE_PER_PERSON,
                               nx200_pax=NX200_PAX,
                               nx200_total=NX200_TOTAL,
                               nx200_deposit=NX200_DEPOSIT,
                               nx200_balance=NX200_BALANCE,
                               nx200_available=_nx200_available(),
                               departure_options=DEPARTURE_OPTIONS,
                               passenger_liff_id=PASSENGER_LIFF_ID,
                               form=form_data)


# ── 訂單明細 ────────────────────────────────────────────────────────────────

@passenger_bp.route("/orders/<order_no>")
def order_detail(order_no):
    from app.models.vehicle import Vehicle
    from app.models.dispatch import Dispatch

    order = Order.query.filter_by(order_no=order_no.upper()).first_or_404()

    # 同行成員（同一 group_id 的所有訂單）
    group_orders = []
    if order.group_id:
        group_orders = (Order.query
                        .filter_by(group_id=order.group_id)
                        .order_by(Order.created_at.asc()).all())

    # 排車資訊
    vehicle  = Vehicle.query.get(order.vehicle_id) if order.vehicle_id else None
    dispatch = Dispatch.query.get(order.dispatch_id) if order.dispatch_id else None
    driver   = dispatch.driver if dispatch else None

    is_new = request.args.get("new") == "1"

    return render_template("passenger/order_detail.html",
                           order=order,
                           group_orders=group_orders,
                           vehicle=vehicle,
                           driver=driver,
                           is_new=is_new,
                           passenger_liff_id=PASSENGER_LIFF_ID)


# ── 訂單查詢 ────────────────────────────────────────────────────────────────

@passenger_bp.route("/orders/lookup-by-name")
def order_lookup_by_name():
    from flask import jsonify
    name  = request.args.get("name", "").strip()
    phone = request.args.get("phone", "").strip()
    if not name or not phone:
        return jsonify({"error": "請填寫姓名與手機號碼"}), 400
    orders = (Order.query
              .filter(Order.contact_name == name,
                      Order.phone == phone)
              .order_by(Order.departure_date.asc())
              .all())
    if not orders:
        return jsonify({"orders": []})
    return jsonify({"orders": [
        {"order_no": o.order_no,
         "departure_date": o.departure_date,
         "passenger_count": o.passenger_count,
         "payment_status": o.payment_status}
        for o in orders
    ]})


@passenger_bp.route("/orders/lookup")
def order_lookup():
    return redirect(url_for("passenger.order_search"))


@passenger_bp.route("/orders/search")
def order_search():
    from app.models.vehicle import Vehicle

    line_user_id = request.args.get("line_user_id", "").strip()
    order_no     = request.args.get("order_no", "").strip().upper()
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

    elif order_no or phone4:
        # Priority 2：必須同時提供 訂單編號 + 手機後四碼
        searched = True
        missing = []
        if not order_no:
            missing.append("訂單編號")
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
                         Order.phone.endswith(phone4),
                     )
                     .first())
            if not order:
                error = "查無符合資料，請確認訂單編號、手機後四碼是否正確"
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
