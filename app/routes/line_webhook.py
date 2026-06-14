"""
LINE Messaging API Webhook Handler

用途：接收 LINE 推送的事件，記錄群組 ID 供後續設定 ADMIN_GROUP_ID 使用。
不修改 line_notification.py 既有推播功能。
"""

import hashlib
import hmac
import json
import logging
import os

from flask import Blueprint, jsonify, request
from app import csrf

logger = logging.getLogger(__name__)

line_webhook_bp = Blueprint("line_webhook", __name__)

# 記憶最近一次收到的群組事件（in-memory，重啟後清空）
_last_event: dict = {}


def _verify_signature(body: bytes, signature: str) -> bool:
    """驗證 X-Line-Signature（HMAC-SHA256）。"""
    secret = os.getenv("LINE_CHANNEL_SECRET", "").strip()
    if not secret:
        logger.warning("LINE_CHANNEL_SECRET 未設定，跳過簽名驗證")
        return True  # 未設定時允許通過，避免開發期間卡住

    digest = hmac.new(
        secret.encode("utf-8"), body, hashlib.sha256
    ).digest()
    import base64
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected, signature or "")


@line_webhook_bp.route("/callback", methods=["POST"])
@csrf.exempt
def callback():
    """LINE Messaging API Webhook 入口。"""
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data()

    if not _verify_signature(body, signature):
        logger.warning("LINE Webhook 簽名驗證失敗")
        return "Forbidden", 403

    try:
        payload = json.loads(body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error("LINE Webhook 解析 JSON 失敗: %s", e)
        return "OK", 200  # LINE 要求無論如何都回 200

    for event in payload.get("events", []):
        event_type = event.get("type", "unknown")
        source = event.get("source", {})
        source_type = source.get("type", "unknown")
        user_id = source.get("userId", "")
        group_id = source.get("groupId", "")

        logger.info(
            "LINE Event — type=%s source_type=%s userId=%s groupId=%s",
            event_type, source_type, user_id, group_id,
        )

        if source_type == "group" and group_id:
            logger.info("LINE GROUP ID: %s", group_id)

            # 更新最近一次群組事件記錄
            _last_event.update({
                "event_type": event_type,
                "source_type": source_type,
                "group_id": group_id,
                "user_id": user_id,
            })

    return "OK", 200


@line_webhook_bp.route("/api/debug/line", methods=["GET"])
def debug_line():
    """顯示最近一次收到的 LINE 群組事件，供確認 groupId 使用。"""
    if not _last_event:
        return jsonify({"message": "尚未收到任何 LINE 群組事件"}), 200

    return jsonify({
        "event_type": _last_event.get("event_type"),
        "source_type": _last_event.get("source_type"),
        "group_id": _last_event.get("group_id"),
        "user_id": _last_event.get("user_id"),
        "hint": "將上方 group_id 設為環境變數 ADMIN_GROUP_ID 即可啟用群組通知",
    }), 200
