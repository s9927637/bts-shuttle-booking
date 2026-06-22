"""
LINE Messaging API 管理群組通知服務。
所有公開函式皆保證不拋出例外 — 失敗時記錄 log，不中斷主流程。
"""

import logging
import os

import requests

logger = logging.getLogger(__name__)

_LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"
_REQUEST_TIMEOUT = 5  # 秒


def _get_config():
    token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "").strip()
    group_id = os.getenv("ADMIN_GROUP_ID", "").strip()
    return token, group_id


def send_admin_notification(message: str) -> None:
    """推送純文字訊息至管理 LINE 群組。失敗時僅記錄 log，不影響呼叫方流程。"""
    token, group_id = _get_config()
    if not token or not group_id:
        logger.debug("LINE 通知跳過：未設定 LINE_CHANNEL_ACCESS_TOKEN 或 ADMIN_GROUP_ID")
        return

    try:
        resp = requests.post(
            _LINE_PUSH_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "to": group_id,
                "messages": [{"type": "text", "text": message}],
            },
            timeout=_REQUEST_TIMEOUT,
        )
        if resp.status_code != 200:
            logger.error("LINE 推送失敗 status=%s body=%s", resp.status_code, resp.text[:200])
    except Exception as exc:
        logger.error("LINE 推送例外：%s", exc, exc_info=True)


# ── 通知訊息工廠 ────────────────────────────────────────────────────────────

def _event_label(order) -> str:
    """從訂單取得活動名稱，供通知訊息使用。"""
    if order.event_page:
        return order.event_page.event_display_name
    return "BTS 高雄演唱會包車"   # fallback：既有 BTS 訂單


def notify_new_order(order) -> None:
    """🎉 新訂單建立通知"""
    vehicle_label = "NX200 專屬包車" if order.vehicle_type == "nx200" else "九座商旅車"
    msg = (
        f"🎉 新訂單\n\n"
        f"【{_event_label(order)}】\n"
        f"訂單編號：{order.order_no}\n"
        f"姓名：{order.contact_name}\n"
        f"日期：{order.departure_date}\n"
        f"人數：{order.passenger_count} 人\n"
        f"車型：{vehicle_label}\n"
        f"總金額：NT${order.total_amount:,}\n"
        f"付款狀態：{order.payment_status}"
    )
    send_admin_notification(msg)


def notify_nx200_booked(order) -> None:
    """🚗 NX200 被預約通知"""
    msg = (
        f"🚗 NX200 已被預約\n\n"
        f"訂單編號：{order.order_no}\n"
        f"姓名：{order.contact_name}\n"
        f"人數：{order.passenger_count} 人"
    )
    send_admin_notification(msg)


def notify_payment_report(order, payment) -> None:
    """💰 匯款回報送出通知"""
    msg = (
        f"💰 新匯款回報\n\n"
        f"【{_event_label(order)}】\n"
        f"訂單編號：{order.order_no}\n"
        f"姓名：{order.contact_name}\n"
        f"回報金額：NT${order.deposit_amount:,}\n"
        f"匯款末五碼：{payment.bank_last5 or '—'}\n\n"
        f"請至付款管理確認"
    )
    send_admin_notification(msg)


def notify_deposit_confirmed(order, admin_name: str = "管理員") -> None:
    """✅ 訂金確認通知"""
    msg = (
        f"✅ 訂金已確認\n\n"
        f"【{_event_label(order)}】\n"
        f"訂單編號：{order.order_no}\n"
        f"姓名：{order.contact_name}\n"
        f"確認人員：{admin_name}"
    )
    send_admin_notification(msg)


def notify_order_cancelled(order) -> None:
    """❌ 訂單取消通知"""
    msg = (
        f"❌ 訂單取消\n\n"
        f"【{_event_label(order)}】\n"
        f"訂單編號：{order.order_no}\n"
        f"姓名：{order.contact_name}\n"
        f"取消人數：{order.passenger_count} 人"
    )
    send_admin_notification(msg)


def notify_group_formed(departure_date: str, current_passengers: int) -> None:
    """🎊 車次成團通知"""
    msg = (
        f"🎊 車次已成團\n\n"
        f"日期：{departure_date}\n"
        f"目前人數：{current_passengers}/8\n\n"
        f"可安排出車"
    )
    send_admin_notification(msg)


def check_and_notify_group_formed(order, prev_pax: int) -> None:
    """
    檢查此次新增訂單是否使該場次首次達到成團門檻（>= 8 人）。
    prev_pax：加入此訂單前的有效乘客數（九座商旅車）。
    """
    THRESHOLD = 8
    new_pax = prev_pax + order.passenger_count
    if prev_pax < THRESHOLD <= new_pax:
        notify_group_formed(order.departure_date, new_pax)
