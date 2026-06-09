"""
LINE Messaging API — Push Message 通知系統
兩個 LINE Official Account：
  - 乘客 OA: PASSENGER_LINE_CHANNEL_ACCESS_TOKEN
  - 司機 OA: DRIVER_LINE_CHANNEL_ACCESS_TOKEN
"""
import os
import requests
from app import db
from app.models.notification import Notification

_LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"

PASSENGER_TOKEN = os.environ.get("PASSENGER_LINE_CHANNEL_ACCESS_TOKEN", "")
DRIVER_TOKEN    = os.environ.get("DRIVER_LINE_CHANNEL_ACCESS_TOKEN", "")


# ── 底層發送 ─────────────────────────────────────────────────────────────────

def _push(token: str, user_id: str, text: str) -> bool:
    if not token or not user_id:
        return False
    try:
        resp = requests.post(
            _LINE_PUSH_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={"to": user_id, "messages": [{"type": "text", "text": text}]},
            timeout=10,
        )
        return resp.status_code == 200
    except Exception:
        return False


def _push_driver(user_id: str, text: str) -> bool:
    return _push(DRIVER_TOKEN, user_id, text)


def _push_passenger(user_id: str, text: str) -> bool:
    return _push(PASSENGER_TOKEN, user_id, text)


# ── 記錄寫入 ─────────────────────────────────────────────────────────────────

def _log(receiver_type, receiver_name, receiver_id, message,
         status, dispatch_id=None, order_id=None):
    rec = Notification(
        type=receiver_type,
        receiver_type=receiver_type,
        receiver_id=receiver_id,
        receiver_name=receiver_name,
        message=message,
        status=status,
        dispatch_id=dispatch_id,
        order_id=order_id,
    )
    db.session.add(rec)
    db.session.flush()
    return rec


# ── 司機通知 ─────────────────────────────────────────────────────────────────

def send_driver_notification(driver, dispatch) -> dict:
    """
    通知司機排車資訊（使用 DRIVER OA）。
    回傳 {"status": "success"|"failed"|"skipped", "name": ..., "notification_id": ...}
    """
    orders = [do.order for do in dispatch.dispatch_orders if do.order]
    passenger_total = sum(o.passenger_count for o in orders)
    balance_total   = sum(o.balance_amount  for o in orders)

    passenger_lines = "\n".join(
        f"  • {o.contact_name}（{o.passenger_count} 人）{o.phone}"
        for o in orders
    )

    message = (
        f"【BTS高雄演唱會 派車通知】\n"
        f"─────────────────\n"
        f"日期：{dispatch.departure_date}\n"
        f"車號：{dispatch.vehicle.plate_number}\n"
        f"司機：{driver.name}\n"
        f"乘客數：{passenger_total} 人\n"
        f"─────────────────\n"
        f"乘客名單：\n"
        f"{passenger_lines}\n"
        f"─────────────────\n"
        f"尾款資訊：\n"
        f"每人尾款：NT${1700:,}\n"
        f"總尾款：NT${balance_total:,}\n"
        f"（搭車當日向乘客收取）"
    )

    if not getattr(driver, "line_user_id", None):
        rec = _log("driver", driver.name, None, message, "skipped",
                   dispatch_id=dispatch.id)
        db.session.commit()
        return {"status": "skipped", "name": driver.name, "notification_id": rec.id}

    ok     = _push_driver(driver.line_user_id, message)
    status = "success" if ok else "failed"
    rec    = _log("driver", driver.name, driver.line_user_id, message, status,
                  dispatch_id=dispatch.id)
    db.session.commit()
    return {"status": status, "name": driver.name, "notification_id": rec.id}


# ── 乘客通知 ─────────────────────────────────────────────────────────────────

def send_passenger_notification(order, dispatch) -> dict:
    """
    通知乘客乘車資訊（使用 PASSENGER OA）。
    回傳 {"status": "success"|"failed"|"skipped", "name": ..., "notification_id": ...}
    """
    message = (
        f"【BTS高雄演唱會 接駁通知】\n"
        f"─────────────────\n"
        f"訂單：{order.order_no}\n"
        f"日期：{dispatch.departure_date}\n"
        f"車號：{dispatch.vehicle.plate_number}\n"
        f"司機：{dispatch.vehicle.driver_name}\n"
        f"司機電話：{dispatch.vehicle.driver_phone}\n"
        f"集合地點：台北車站\n"
        f"─────────────────\n"
        f"尾款提醒：\n"
        f"尾款金額：NT${order.balance_amount:,}\n"
        f"搭車當日現金支付給司機\n"
        f"─────────────────\n"
        f"請準時到達，祝演唱會愉快！🎵"
    )

    if not getattr(order, "line_user_id", None):
        rec = _log("passenger", order.contact_name, None, message, "skipped",
                   dispatch_id=dispatch.id, order_id=order.id)
        db.session.commit()
        return {"status": "skipped", "name": order.contact_name, "notification_id": rec.id}

    ok     = _push_passenger(order.line_user_id, message)
    status = "success" if ok else "failed"
    rec    = _log("passenger", order.contact_name, order.line_user_id, message, status,
                  dispatch_id=dispatch.id, order_id=order.id)
    db.session.commit()
    return {"status": status, "name": order.contact_name, "notification_id": rec.id}


# ── 批次通知（dispatch 層級）────────────────────────────────────────────────

def notify_dispatch_driver(dispatch) -> dict:
    """通知某 dispatch 的司機，回傳單一結果 dict。"""
    driver = dispatch.driver
    if not driver:
        rec = _log("driver", dispatch.vehicle.driver_name or "未知司機", None,
                   "無綁定 Driver 記錄", "skipped", dispatch_id=dispatch.id)
        db.session.commit()
        return {"status": "skipped", "name": dispatch.vehicle.driver_name or "未知",
                "notification_id": rec.id}
    return send_driver_notification(driver, dispatch)


def notify_dispatch_passengers(dispatch) -> list:
    """批次通知某 dispatch 所有乘客，回傳結果列表。"""
    orders = [do.order for do in dispatch.dispatch_orders if do.order]
    return [send_passenger_notification(order, dispatch) for order in orders]


# ── 公告推播 ─────────────────────────────────────────────────────────────────

def send_announcement_notification(announcement) -> dict:
    """
    推播公告到指定 LINE 對象。
    回傳 {"sent": int, "failed": int}
    """
    import os
    from app.models.order import Order
    from app.models.driver import Driver

    liff_id = os.environ.get("PASSENGER_LIFF_ID", "")
    excerpt = announcement.content[:100] + ("…" if len(announcement.content) > 100 else "")
    deep_link = f"https://liff.line.me/{liff_id}/announcements/{announcement.id}" if liff_id else ""

    msg = (
        f"【BTS高雄演唱會 公告】\n"
        f"─────────────────\n"
        f"{announcement.title}\n\n"
        f"{excerpt}\n"
    )
    if deep_link:
        msg += f"\n詳情請點：{deep_link}"

    target = announcement.line_target or "全部乘客"
    sent, failed = 0, 0

    if target in ("全部乘客", "11/19 乘客", "11/21 乘客", "11/22 乘客"):
        q = Order.query.filter(Order.line_user_id.isnot(None))
        date_map = {"11/19 乘客": "11/19(四)", "11/21 乘客": "11/21(六)", "11/22 乘客": "11/22(日)"}
        if target in date_map:
            q = q.filter(Order.departure_date == date_map[target])
        for order in q.all():
            ok = _push_passenger(order.line_user_id, msg)
            if ok:
                sent += 1
            else:
                failed += 1

    elif target == "全部司機":
        for driver in Driver.query.filter(Driver.line_user_id.isnot(None)).all():
            ok = _push_driver(driver.line_user_id, msg)
            if ok:
                sent += 1
            else:
                failed += 1

    return {"sent": sent, "failed": failed}


# ── 重新發送（retry）────────────────────────────────────────────────────────

def resend_notification(notification_id: int) -> dict:
    """重新發送單一失敗的通知記錄。"""
    notif = Notification.query.get(notification_id)
    if not notif or notif.status != "failed":
        return {"status": "error", "msg": "通知不存在或非失敗狀態"}

    if notif.receiver_type == "driver":
        ok = _push_driver(notif.receiver_id, notif.message)
    else:
        ok = _push_passenger(notif.receiver_id, notif.message)

    notif.status = "success" if ok else "failed"
    db.session.commit()
    return {"status": notif.status}
