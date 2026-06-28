import os
import uuid
import random
import string
from datetime import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from app import db
from app.utils.error_handler import friendly_error
from app.models.order import Order
from app.models.payment import Payment
from app.models.announcement import Announcement
from app.services.line_notification import (
    notify_new_order,
    notify_nx200_booked,
    notify_payment_report,
    check_and_notify_group_formed,
)

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
    from app.models.event_page import EventPage
    announcements = (
        Announcement.query
        .filter(Announcement.status == "已發布")
        .order_by(Announcement.is_pinned.desc(), Announcement.created_at.desc())
        .limit(3).all()
    )
    # Phase 6：從 DB 讀取活動，取代硬寫 BTS
    published_events = (
        EventPage.query
        .filter(EventPage.deleted_at.is_(None), EventPage.status == "已發布")
        .order_by(EventPage.event_date.asc(), EventPage.created_at.desc())
        .limit(6).all()
    )
    return render_template("passenger/home.html",
                           announcements=announcements,
                           published_events=published_events)


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

    # 活動頁模式：?event_id=<id>
    event_page = None
    event_id = request.args.get("event_id", type=int)
    if event_id:
        from app.models.event_page import EventPage
        ep = EventPage.query.get(event_id)
        if ep and ep.is_published:
            event_page = ep

    price_per   = (event_page.price   or PRICE_PER_PERSON)   if event_page else PRICE_PER_PERSON
    deposit_per = (event_page.deposit or DEPOSIT_PER_PERSON)  if event_page else DEPOSIT_PER_PERSON
    balance_per = price_per - deposit_per

    # 活動搭車日期 / 地點 / 表單設定
    ep_booking_dates    = []
    ep_pickup_locations = []
    ep_price_rules_json = {}   # {date_id: {loc_id: {price, deposit}}}
    ep_form_config      = {}   # {field_name: {visible, required, label}}
    if event_page:
        from app.models.event_booking import EventBookingDate, EventPickupLocation, EventPriceRule, EventFormConfig
        import json as _json
        ep_booking_dates    = EventBookingDate.query.filter_by(event_page_id=event_page.id, is_active=True).order_by(EventBookingDate.sort_order).all()
        ep_pickup_locations = EventPickupLocation.query.filter_by(event_page_id=event_page.id, is_active=True).order_by(EventPickupLocation.sort_order).all()
        for rule in EventPriceRule.query.filter_by(event_page_id=event_page.id).all():
            dk = str(rule.booking_date_id or 'any')
            lk = str(rule.location_id or 'any')
            ep_price_rules_json.setdefault(dk, {})[lk] = {'price': rule.price, 'deposit': rule.deposit}
        for fc in EventFormConfig.query.filter_by(event_page_id=event_page.id).all():
            ep_form_config[fc.field_name] = {
                'visible':  fc.is_visible,
                'required': fc.is_required,
                'label':    fc.label_override,
            }

    return render_template("passenger/booking.html",
                           price_per_person=price_per,
                           deposit_per_person=deposit_per,
                           balance_per_person=balance_per,
                           nx200_pax=NX200_PAX,
                           nx200_total=NX200_TOTAL,
                           nx200_deposit=NX200_DEPOSIT,
                           nx200_balance=NX200_BALANCE,
                           nx200_available=_nx200_available(),
                           departure_options=DEPARTURE_OPTIONS,
                           passenger_liff_id=PASSENGER_LIFF_ID,
                           prefill_friend_code=friend_code,
                           event_page=event_page,
                           ep_booking_dates=ep_booking_dates,
                           ep_pickup_locations=ep_pickup_locations,
                           ep_price_rules_json=ep_price_rules_json,
                           ep_form_config=ep_form_config,
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

    # 活動頁模式
    event_page_id_raw = request.form.get("event_page_id", "").strip()
    event_page = None
    if event_page_id_raw and event_page_id_raw.isdigit():
        from app.models.event_page import EventPage
        event_page = EventPage.query.get(int(event_page_id_raw))

    try:
        dep = form_data["departure_date"]

        if event_page:
            # 活動模式：驗證預約時間窗口
            from datetime import datetime as _dt
            now = _dt.utcnow()
            if event_page.booking_open_at and now < event_page.booking_open_at:
                raise ValueError("預約尚未開放，請稍後再試。")
            if event_page.booking_close_at and now > event_page.booking_close_at:
                raise ValueError("預約已截止，感謝您的關注。")

            if not dep:
                raise ValueError("請填寫出發日期。")

            # 取得上車地點（存快照名稱）
            pickup_location_val = request.form.get("pickup_location", "").strip() or None

            # 查詢價格規則（優先順序：日期+地點 > 日期 > 地點 > 全局）
            from app.models.event_booking import EventBookingDate, EventPickupLocation, EventPriceRule
            booking_date_obj = EventBookingDate.query.filter_by(event_page_id=event_page.id, date_value=dep, is_active=True).first()
            location_obj = None
            if pickup_location_val:
                location_obj = EventPickupLocation.query.filter_by(event_page_id=event_page.id, name=pickup_location_val, is_active=True).first()

            rule = None
            if booking_date_obj and location_obj:
                rule = EventPriceRule.query.filter_by(event_page_id=event_page.id, booking_date_id=booking_date_obj.id, location_id=location_obj.id).first()
            if not rule and booking_date_obj:
                rule = EventPriceRule.query.filter_by(event_page_id=event_page.id, booking_date_id=booking_date_obj.id, location_id=None).first()
            if not rule and location_obj:
                rule = EventPriceRule.query.filter_by(event_page_id=event_page.id, booking_date_id=None, location_id=location_obj.id).first()
            if not rule:
                rule = EventPriceRule.query.filter_by(event_page_id=event_page.id, booking_date_id=None, location_id=None).first()

            if rule:
                price_per   = rule.price
                deposit_per = rule.deposit
            else:
                price_per   = event_page.price   or PRICE_PER_PERSON
                deposit_per = event_page.deposit or DEPOSIT_PER_PERSON
            balance_per = price_per - deposit_per
        else:
            # 原 BTS 模式：驗證場次
            pickup_location_val = None
            if dep not in AVAILABLE_DATES:
                raise ValueError("所選場次目前不開放預約，請選擇 11/22（日）場次。")
            price_per   = PRICE_PER_PERSON
            deposit_per = DEPOSIT_PER_PERSON
            balance_per = BALANCE_PER_PERSON

        # 車輛方案計價
        if vehicle_type == "nx200" and not event_page:
            if not _nx200_available():
                raise ValueError("NX200 專屬包車已售完，請選擇九座商旅車方案。")
            passenger_count = NX200_PAX
            total_amount    = NX200_TOTAL
            deposit_amount  = NX200_DEPOSIT
            balance_amount  = NX200_BALANCE
        else:
            vehicle_type    = "minibus"
            passenger_count = int(form_data["passenger_count"])
            # 活動模式：驗證人數限制
            if event_page:
                min_g = event_page.min_group_size or 1
                max_g = event_page.max_group_size
                if passenger_count < min_g:
                    raise ValueError(f"最少需預約 {min_g} 人。")
                if max_g and passenger_count > max_g:
                    raise ValueError(f"每次最多預約 {max_g} 人。")
            total_amount    = passenger_count * price_per
            deposit_amount  = passenger_count * deposit_per
            balance_amount  = passenger_count * balance_per

        # 折扣碼套用
        from app.models.coupon import Coupon
        coupon_code_input = request.form.get("coupon_code", "").strip().upper()
        discount_amount   = 0
        applied_coupon    = None
        if coupon_code_input:
            coupon = Coupon.query.filter_by(code=coupon_code_input).first()
            if coupon and coupon.is_valid_now:
                discount_amount = coupon.calc_discount(total_amount)
                total_amount    = max(0, total_amount - discount_amount)
                balance_amount  = max(0, total_amount - deposit_amount)
                applied_coupon  = coupon

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
            order_no          = "TEMP",
            contact_name      = form_data["contact_name"],
            phone             = form_data["phone"],
            emergency_phone   = form_data["emergency_phone"] or None,
            departure_date    = form_data["departure_date"],
            passenger_count   = passenger_count,
            remark            = form_data["remark"] or None,
            total_amount      = total_amount,
            deposit_amount    = deposit_amount,
            balance_amount    = balance_amount,
            payment_status    = "待付款",
            vehicle_type      = vehicle_type,
            group_id          = group_id,
            line_user_id      = line_user_id,
            display_name      = display_name,
            terms_accepted_at = datetime.utcnow(),
            terms_version     = "v1.0",
            coupon_code       = applied_coupon.code if applied_coupon else None,
            discount_amount   = discount_amount,
            event_page_id     = event_page.id if event_page else None,
            pickup_location   = pickup_location_val if event_page else None,
        )
        if applied_coupon:
            applied_coupon.use_count += 1
        db.session.add(order)
        db.session.flush()                       # 取得 id，尚未 commit
        order.order_no = _gen_order_no(order.id)

        # 成團前計算（不含本訂單，以九座商旅車為準）
        if vehicle_type == "minibus":
            from sqlalchemy import func as _func
            prev_pax = db.session.query(_func.sum(Order.passenger_count)).filter(
                Order.departure_date == order.departure_date,
                Order.vehicle_type == "minibus",
                Order.payment_status.in_(["待付款", "待確認", "訂金已確認", "已完成"]),
                Order.id != order.id,
            ).scalar() or 0

        db.session.commit()

        # 活動統計更新（失敗不影響主流程）
        if order.event_page_id:
            try:
                from app.services.event_metrics_service import refresh_metrics
                refresh_metrics(order.event_page_id)
                db.session.commit()
            except Exception:
                db.session.rollback()

        # LINE 通知（commit 成功後送出，失敗不影響主流程）
        notify_new_order(order)
        if vehicle_type == "nx200":
            notify_nx200_booked(order)
        else:
            check_and_notify_group_formed(order, prev_pax)

        return redirect(url_for("passenger.order_detail",
                                order_no=order.order_no, new=1))

    except (ValueError, Exception) as e:
        db.session.rollback()
        msg = str(e) if isinstance(e, ValueError) else f"預約失敗，請重試。（{e}）"
        flash(msg, "error")
        price_per   = (event_page.price   or PRICE_PER_PERSON)   if event_page else PRICE_PER_PERSON
        deposit_per = (event_page.deposit or DEPOSIT_PER_PERSON)  if event_page else DEPOSIT_PER_PERSON
        # 重新查詢活動設定，供表單重新渲染
        _ep_booking_dates = _ep_pickup_locations = []
        _ep_price_rules_json = _ep_form_config = {}
        if event_page:
            from app.models.event_booking import EventBookingDate, EventPickupLocation, EventPriceRule, EventFormConfig
            _ep_booking_dates    = EventBookingDate.query.filter_by(event_page_id=event_page.id, is_active=True).order_by(EventBookingDate.sort_order).all()
            _ep_pickup_locations = EventPickupLocation.query.filter_by(event_page_id=event_page.id, is_active=True).order_by(EventPickupLocation.sort_order).all()
            for rule in EventPriceRule.query.filter_by(event_page_id=event_page.id).all():
                dk = str(rule.booking_date_id or 'any')
                lk = str(rule.location_id or 'any')
                _ep_price_rules_json.setdefault(dk, {})[lk] = {'price': rule.price, 'deposit': rule.deposit}
            for fc in EventFormConfig.query.filter_by(event_page_id=event_page.id).all():
                _ep_form_config[fc.field_name] = {'visible': fc.is_visible, 'required': fc.is_required, 'label': fc.label_override}
        return render_template("passenger/booking.html",
                               price_per_person=price_per,
                               deposit_per_person=deposit_per,
                               balance_per_person=price_per - deposit_per,
                               nx200_pax=NX200_PAX,
                               nx200_total=NX200_TOTAL,
                               nx200_deposit=NX200_DEPOSIT,
                               nx200_balance=NX200_BALANCE,
                               nx200_available=_nx200_available(),
                               departure_options=DEPARTURE_OPTIONS,
                               passenger_liff_id=PASSENGER_LIFF_ID,
                               event_page=event_page,
                               ep_booking_dates=_ep_booking_dates,
                               ep_pickup_locations=_ep_pickup_locations,
                               ep_price_rules_json=_ep_price_rules_json,
                               ep_form_config=_ep_form_config,
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

    # 先解析 event context，讓後續查詢可以 scope
    event_slug = request.args.get("event_slug", "").strip()
    event_page_ctx = None
    if event_slug:
        from app.models.event_page import EventPage as _EP
        _ep = _EP.query.filter_by(slug=event_slug).filter(_EP.deleted_at.is_(None)).first()
        if _ep and _ep.is_published:
            event_page_ctx = _ep

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
        q = Order.query.filter_by(line_user_id=line_user_id)
        if event_page_ctx:
            q = q.filter(Order.event_page_id == event_page_ctx.id)
        orders = q.order_by(Order.created_at.desc()).all()

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
            q = Order.query.filter(
                Order.order_no == order_no,
                Order.phone.endswith(phone4),
            )
            if event_page_ctx:
                q = q.filter(Order.event_page_id == event_page_ctx.id)
            order = q.first()
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
        event_page=event_page_ctx,
    )


# ── 匯款回報 ────────────────────────────────────────────────────────────────

@passenger_bp.route("/payment/report", methods=["GET"])
def payment_report():
    prefill_order_no = request.args.get("order_no", "")
    line_user_id     = request.args.get("line_user_id", "")
    group_id         = request.args.get("group_id", "")
    show_group       = request.args.get("show_group", "")   # "created" / "joined" / ""

    # 先解析 event context
    event_slug_pr = request.args.get("event_slug", "").strip()
    event_page_pr = None
    if event_slug_pr:
        from app.models.event_page import EventPage as _EP2
        _ep2 = _EP2.query.filter_by(slug=event_slug_pr).filter(_EP2.deleted_at.is_(None)).first()
        if _ep2 and _ep2.is_published:
            event_page_pr = _ep2

    line_orders = []
    if line_user_id:
        q = Order.query.filter_by(line_user_id=line_user_id)\
                       .filter(Order.payment_status.in_(["待付款", "待確認"]))
        if event_page_pr:
            q = q.filter(Order.event_page_id == event_page_pr.id)
        line_orders = q.order_by(Order.created_at.desc()).all()

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
                           passenger_liff_id=PASSENGER_LIFF_ID,
                           event_page=event_page_pr)


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
            order_id      = order.id,
            payer_name    = payer_name,
            bank_last5    = bank_last5,
            status        = "待確認",
            event_page_id = order.event_page_id,
        )
        order.payment_status = "待確認"
        db.session.add(payment)
        db.session.commit()

        notify_payment_report(order, payment)

        flash("匯款資料已送出，我們將盡快確認並通知您。", "success")
        return redirect(url_for("passenger.order_lookup", q=order_no))

    except Exception as e:
        db.session.rollback()
        flash(friendly_error(e, "匯款回報"), "error")
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
        flash(friendly_error(e, "加入同行群組"), "error")

    return redirect(url_for("passenger.join_group", group_id=group_id))


# ── LINE 自動補綁定 API ───────────────────────────────────────────────────────

@passenger_bp.route("/api/line-bind", methods=["POST"])
def api_line_bind():
    """
    LIFF 頁面取得 userId 後呼叫，以電話號碼或訂單編號比對，
    將 line_user_id = NULL 的舊訂單自動補上。
    不需登入，但需同時提供 line_user_id + phone（或 order_no）。
    """
    data = request.get_json(silent=True) or {}
    line_user_id = (data.get("line_user_id") or "").strip()
    phone        = (data.get("phone")        or "").strip()
    order_no     = (data.get("order_no")     or "").strip().upper()
    display_name = (data.get("display_name") or "").strip() or None

    if not line_user_id:
        return jsonify({"ok": False, "error": "缺少必要的識別資訊，請重新操作。"}), 400

    updated = 0

    if phone:
        # Match by phone: update all orders with the same phone that are still unbound
        rows = Order.query.filter(
            Order.phone == phone,
            Order.line_user_id.is_(None)
        ).all()
        for o in rows:
            o.line_user_id = line_user_id
            if display_name and not o.display_name:
                o.display_name = display_name
            updated += 1

    if order_no and not updated:
        # Fallback: match by order_no
        o = Order.query.filter_by(order_no=order_no).first()
        if o and o.line_user_id is None:
            o.line_user_id = line_user_id
            if display_name and not o.display_name:
                o.display_name = display_name
            updated += 1

    if updated:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            return jsonify({"ok": False, "error": "系統暫時無法處理，請稍後再試。"}), 500

    return jsonify({"ok": True, "updated": updated})


# ── 折扣碼驗證 API ─────────────────────────────────────────────────────────

@passenger_bp.route("/api/coupon/validate")
def api_coupon_validate():
    from app.models.coupon import Coupon
    code       = request.args.get("code", "").strip().upper()
    vehicle    = request.args.get("vehicle", "minibus")
    pax        = max(1, request.args.get("pax", 1, type=int))

    if not code:
        return jsonify({"valid": False, "message": "請輸入折扣碼"})

    coupon = Coupon.query.filter_by(code=code).first()
    if not coupon:
        return jsonify({"valid": False, "message": "折扣碼無效"})
    if not coupon.is_valid_now:
        return jsonify({"valid": False, "message": "折扣碼已過期或已達使用上限"})

    # 計算原始總金額
    if vehicle == "nx200":
        total = NX200_TOTAL
    else:
        total = pax * PRICE_PER_PERSON

    discount = coupon.calc_discount(total)

    return jsonify({
        "valid":          True,
        "code":           coupon.code,
        "name":           coupon.name,
        "discount_type":  coupon.discount_type,
        "discount_value": coupon.discount_value,
        "discount_amount": discount,
        "message":        f"已套用折扣碼 {coupon.code}，折扣 NT${discount:,}",
    })
