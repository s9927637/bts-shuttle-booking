"""
集中式錯誤訊息轉換工具。
將底層資料庫 / 系統例外轉為使用者可理解的繁體中文訊息，
確保任何技術性細節不直接暴露於前端。
"""

import logging

logger = logging.getLogger(__name__)


def friendly_error(exc: Exception, context: str = "") -> str:
    """
    將任意 Exception 轉為繁體中文使用者訊息。
    同時將原始錯誤記錄至 server log，方便除錯。

    Parameters
    ----------
    exc     : 捕捉到的例外物件
    context : 操作情境描述，用於 log（例如「開立收據」），不對外顯示
    """
    # 記錄到 server log（含完整 traceback）
    logger.error("[%s] %s: %s", context or "系統錯誤", type(exc).__name__, exc, exc_info=True)

    msg = str(exc).lower()
    exc_type = type(exc).__name__

    # ── PostgreSQL / SQLAlchemy 常見錯誤 ──────────────────────────────

    # ForeignKeyViolation：刪除被其他資料表參考的紀錄
    if "foreignkeyviolation" in exc_type.lower() or "foreign key" in msg or "fkey" in msg:
        return "此資料仍被其他紀錄使用，無法刪除。請先移除相關聯的紀錄後再試。"

    # UniqueViolation / DuplicateKey：唯一值衝突
    if (
        "uniqueviolation" in exc_type.lower()
        or "unique constraint" in msg
        or "duplicate key" in msg
        or "already exists" in msg
    ):
        return "資料已存在，請勿重複建立。"

    # NotNullViolation：必填欄位為空
    if "notnullviolation" in exc_type.lower() or "null value" in msg or "not-null" in msg:
        return "有必填欄位未填寫，請確認後重試。"

    # CheckViolation：違反資料庫檢查約束
    if "checkviolation" in exc_type.lower() or "check constraint" in msg:
        return "輸入的數值超出允許範圍，請確認後重試。"

    # DataError：資料格式錯誤（例如數字太長、日期格式錯誤）
    if "dataerror" in exc_type.lower() or "invalid input syntax" in msg or "value too long" in msg:
        return "輸入的資料格式不正確，請確認後重試。"

    # OperationalError：資料庫連線問題
    if "operationalerror" in exc_type.lower() or "connection" in msg or "timeout" in msg:
        return "資料庫暫時無法連線，請稍後再試。若問題持續發生，請聯絡系統管理員。"

    # PermissionError / PermissionDenied
    if "permission" in exc_type.lower() or "permission denied" in msg:
        return "您沒有權限執行此操作。"

    # IntegrityError（SQLAlchemy 通用）
    if "integrityerror" in exc_type.lower():
        if "foreign key" in msg or "fkey" in msg:
            return "此資料仍被其他紀錄使用，無法刪除。"
        if "unique" in msg or "duplicate" in msg:
            return "資料已存在，請勿重複建立。"
        return "資料完整性錯誤，請確認輸入內容後重試。"

    # ValueError：程式內部驗證失敗（通常是格式問題）
    if exc_type == "ValueError":
        return "輸入的資料格式不正確，請確認後重試。"

    # 其他所有未知錯誤 → 通用訊息，不洩漏技術細節
    return "操作失敗，請稍後再試。若問題持續發生，請聯絡系統管理員。"
