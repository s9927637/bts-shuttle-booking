"""
LINE Notify Service — 通知預留接口
實際發送需設定 LINE Messaging API Channel Access Token。
"""
import os
import requests


LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_API_BASE = "https://api.line.me/v2/bot/message"


def _push(user_id: str, messages: list) -> bool:
    if not LINE_CHANNEL_ACCESS_TOKEN or not user_id:
        return False
    resp = requests.post(
        f"{LINE_API_BASE}/push",
        headers={
            "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        },
        json={"to": user_id, "messages": messages},
        timeout=10,
    )
    return resp.status_code == 200


def send_driver_notification(driver, dispatch) -> bool:
    """
    通知司機排車資訊。
    driver: Driver model instance
    dispatch: Dispatch model instance
    """
    if not getattr(driver, "line_user_id", None):
        return False

    orders = [do.order for do in dispatch.dispatch_orders]
    passenger_total = sum(o.passenger_count for o in orders)
    passenger_list = "\n".join(
        f"• {o.contact_name}（{o.passenger_count} 人）" for o in orders
    )

    text = (
        f"【BTS接駁 排車通知】\n"
        f"出發日期：{dispatch.departure_date}\n"
        f"車牌：{dispatch.vehicle.plate_number}\n"
        f"乘客共 {passenger_total} 人\n\n"
        f"{passenger_list}\n\n"
        f"請準時於集合地點等候。"
    )
    return _push(driver.line_user_id, [{"type": "text", "text": text}])


def send_passenger_notification(order, dispatch) -> bool:
    """
    通知乘客車輛資訊。
    order: Order model instance（需有 line_user_id）
    dispatch: Dispatch model instance
    """
    if not getattr(order, "line_user_id", None):
        return False

    text = (
        f"【BTS接駁 乘車通知】\n"
        f"訂單：{order.order_no}\n"
        f"出發日期：{dispatch.departure_date}\n"
        f"車牌：{dispatch.vehicle.plate_number}\n"
        f"司機：{dispatch.vehicle.driver_name}\n"
        f"司機電話：{dispatch.vehicle.driver_phone}\n\n"
        f"請於指定時間至集合地點候車。"
    )
    return _push(order.line_user_id, [{"type": "text", "text": text}])
