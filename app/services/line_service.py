"""
LINE Messaging API — Push Message 通知系統
環境變數：LINE_CHANNEL_ACCESS_TOKEN
"""
import os
import requests
from app import db
from app.models.notification import Notification

LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_API_URL = "https://api.line.me/v2/bot/message/push"


def _push(user_id: str, text: str) -> bool:
    """發送 LINE Push Message，回傳是否成功。"""
    if not LINE_CHANNEL_ACCESS_TOKEN or not user_id:
        return False
    try:
        resp = requests.post(
            LINE_API_URL,
            headers={
                "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
                "Content-Type": "application/json",
            },
            json={"to": user_id, "messages": [{"type": "text", "text": text}]},
            timeout=10,
        )
        return resp.status_code == 200
    except Exception:
        return False


def _log(notification_type, recipient_name, recipient_id, content,
         dispatch_id=None, order_id=None, status="success"):
    """寫入通知記錄。"""
    rec = Notification(
        notification_type=notification_type,
        recipient_name=recipient_name,
        recipient_id=recipient_id,
        dispatch_id=dispatch_id,
        order_id=order_id,
        status=status,
        content=content,
    )
    db.session.add(rec)


def send_driver_notification(driver, dispatch) -> dict:
    """
    通知司機排車資訊。
    回傳 {"status": "success"|"failed"|"skipped", "name": driver.name}
    """
    orders = [do.order for do in dispatch.dispatch_orders if do.order]
    passenger_total = sum(o.passenger_count for o in orders)
    balance_total   = sum(o.balance_amount for o in orders)
    passenger_list  = "\n".join(
        f"  • {o.contact_name}（{o.passenger_count} 人）" for o in orders
    )

    content = (
        f"【BTS高雄演唱會 排車通知】\n"
        f"出發日期：{dispatch.departure_date}\n"
        f"車牌號碼：{dispatch.vehicle.plate_number}\n"
        f"乘客人數：{passenger_total} 人\n"
        f"尾款待收：NT${balance_total:,}\n"
        f"\n乘客名單：\n{passenger_list}\n"
        f"\n集合地點：台北車站\n"
        f"請準時到達，謝謝！"
    )

    if not getattr(driver, "line_user_id", None):
        _log("driver", driver.name, None, content,
             dispatch_id=dispatch.id, status="skipped")
        db.session.commit()
        return {"status": "skipped", "name": driver.name}

    ok = _push(driver.line_user_id, content)
    status = "success" if ok else "failed"
    _log("driver", driver.name, driver.line_user_id, content,
         dispatch_id=dispatch.id, status=status)
    db.session.commit()
    return {"status": status, "name": driver.name}


def send_passenger_notification(order, dispatch) -> dict:
    """
    通知乘客車輛與司機資訊。
    回傳 {"status": "success"|"failed"|"skipped", "name": order.contact_name}
    """
    content = (
        f"【BTS高雄演唱會 乘車通知】\n"
        f"訂單編號：{order.order_no}\n"
        f"出發日期：{dispatch.departure_date}\n"
        f"車牌號碼：{dispatch.vehicle.plate_number}\n"
        f"司機姓名：{dispatch.vehicle.driver_name}\n"
        f"司機電話：{dispatch.vehicle.driver_phone}\n"
        f"\n集合地點：台北車站\n"
        f"尾款金額：NT${order.balance_amount:,}（搭車當日現金交給司機）\n"
        f"\n請準時到達，祝演唱會愉快！🎵"
    )

    if not getattr(order, "line_user_id", None):
        _log("passenger", order.contact_name, None, content,
             dispatch_id=dispatch.id, order_id=order.id, status="skipped")
        db.session.commit()
        return {"status": "skipped", "name": order.contact_name}

    ok = _push(order.line_user_id, content)
    status = "success" if ok else "failed"
    _log("passenger", order.contact_name, order.line_user_id, content,
         dispatch_id=dispatch.id, order_id=order.id, status=status)
    db.session.commit()
    return {"status": status, "name": order.contact_name}


def notify_dispatch_driver(dispatch) -> dict:
    """批次通知某 dispatch 的司機（含備用司機欄位）。"""
    driver = dispatch.driver
    if not driver:
        # 從 vehicle 的 driver_name 找不到 Driver model，記錄為 skipped
        _log("driver", dispatch.vehicle.driver_name or "未知司機", None,
             "無綁定 Driver 記錄", dispatch_id=dispatch.id, status="skipped")
        db.session.commit()
        return {"status": "skipped", "name": dispatch.vehicle.driver_name or "未知"}
    return send_driver_notification(driver, dispatch)


def notify_dispatch_passengers(dispatch) -> list:
    """批次通知某 dispatch 所有乘客，回傳結果列表。"""
    orders = [do.order for do in dispatch.dispatch_orders if do.order]
    results = []
    for order in orders:
        results.append(send_passenger_notification(order, dispatch))
    return results
