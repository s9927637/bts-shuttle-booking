"""
Driver LIFF 綁定路由
路由：GET/POST /driver/bind
用途：司機透過 Driver LINE OA 的 LIFF 進入，完成 LINE userId 綁定
"""
import os
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify
from app import db
from app.models.driver import Driver

driver_bp = Blueprint("driver", __name__, url_prefix="/driver")

DRIVER_LIFF_ID = os.environ.get("DRIVER_LIFF_ID", "")


@driver_bp.route("/bind")
def bind():
    """LIFF 綁定頁面：透過 LIFF 取得 userId + displayName 後呼叫 /driver/bind/confirm。"""
    return render_template("driver/bind.html", liff_id=DRIVER_LIFF_ID)


@driver_bp.route("/bind/confirm", methods=["POST"])
def bind_confirm():
    """
    接收 LIFF 取得的 userId + displayName，
    比對已登記的司機（by phone），完成綁定。
    JSON: {line_user_id, display_name, phone}
    回傳: {ok, message}
    """
    data         = request.get_json(force=True)
    line_user_id = (data.get("line_user_id") or "").strip()
    display_name = (data.get("display_name") or "").strip()
    phone        = (data.get("phone") or "").strip()

    if not line_user_id:
        return jsonify({"ok": False, "message": "無法取得 LINE 用戶 ID，請確認已登入 LINE。"})

    # 依電話號碼找到司機
    driver = Driver.query.filter_by(phone=phone).first()
    if not driver:
        return jsonify({"ok": False, "message": "找不到此電話號碼對應的司機，請聯絡管理員。"})

    if driver.is_line_bound and driver.line_user_id == line_user_id:
        return jsonify({"ok": True, "message": f"您好 {driver.name}，LINE 帳號已經綁定過了。"})

    driver.line_user_id  = line_user_id
    driver.bind_status   = "已綁定"
    driver.is_line_bound = True
    driver.bound_at      = datetime.utcnow()
    db.session.commit()

    return jsonify({"ok": True, "message": f"綁定成功！歡迎 {driver.name}，您將透過此 LINE 帳號接收派車通知。"})
