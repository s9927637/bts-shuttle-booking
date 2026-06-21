"""
component_checker — 各模組健康檢查函式。

每個 check_*() 函式回傳：
  {"status": "HEALTHY"|"WARNING"|"ERROR"|"NOT_IMPLEMENTED",
   "response_time": float (秒),
   "message": str}

原則：
- 純讀取，不寫入任何資料
- 不影響訂單 / 付款 / 收據 / 通知
- 模組尚未實作 → NOT_IMPLEMENTED，不拋例外
"""
from __future__ import annotations

import time


def check_database() -> dict:
    """測試 DB 連線：執行 SELECT 1。"""
    t0 = time.monotonic()
    try:
        from app import db
        from sqlalchemy import text
        db.session.execute(text("SELECT 1"))
        elapsed = time.monotonic() - t0
        if elapsed > 1.0:
            return {"status": "WARNING", "response_time": elapsed,
                    "message": f"DB 回應緩慢（{int(elapsed*1000)} ms）"}
        return {"status": "HEALTHY", "response_time": elapsed,
                "message": f"DB 正常（{int(elapsed*1000)} ms）"}
    except Exception as exc:
        return {"status": "ERROR", "response_time": time.monotonic() - t0,
                "message": f"DB 連線失敗：{exc}"}


def check_crawler() -> dict:
    """確認最近爬蟲成功執行時間。"""
    t0 = time.monotonic()
    try:
        from app.models.crawl_job import CrawlJob
        last = (
            CrawlJob.query
            .filter_by(status="success")
            .order_by(CrawlJob.finished_at.desc())
            .first()
        )
        elapsed = time.monotonic() - t0
        if last is None:
            return {"status": "WARNING", "response_time": elapsed,
                    "message": "尚無成功執行紀錄"}
        from datetime import datetime, timedelta
        age = datetime.utcnow() - last.finished_at
        if age > timedelta(days=7):
            return {"status": "WARNING", "response_time": elapsed,
                    "message": f"最近成功執行距今 {age.days} 天"}
        return {"status": "HEALTHY", "response_time": elapsed,
                "message": f"最近成功：{last.source_name}，{last.finished_at.strftime('%m/%d %H:%M')}"}
    except Exception as exc:
        return {"status": "ERROR", "response_time": time.monotonic() - t0,
                "message": str(exc)}


def check_concert_hub() -> dict:
    """確認 Concert Data Hub 資料筆數。"""
    t0 = time.monotonic()
    try:
        from app.models.concert_data_hub import ConcertDataHub
        total = ConcertDataHub.query.filter_by(status="active").count()
        elapsed = time.monotonic() - t0
        if total == 0:
            return {"status": "WARNING", "response_time": elapsed,
                    "message": "Concert Hub 無 active 資料"}
        return {"status": "HEALTHY", "response_time": elapsed,
                "message": f"Active 演唱會：{total} 筆"}
    except Exception as exc:
        return {"status": "ERROR", "response_time": time.monotonic() - t0,
                "message": str(exc)}


def check_business_intelligence() -> dict:
    """確認 BusinessInsight 資料筆數。"""
    t0 = time.monotonic()
    try:
        from app.models.business_insight import BusinessInsight
        total = BusinessInsight.query.count()
        elapsed = time.monotonic() - t0
        if total == 0:
            return {"status": "WARNING", "response_time": elapsed,
                    "message": "尚無商機分析資料，請執行重新計算"}
        return {"status": "HEALTHY", "response_time": elapsed,
                "message": f"商機分析：{total} 筆"}
    except Exception as exc:
        return {"status": "ERROR", "response_time": time.monotonic() - t0,
                "message": str(exc)}


def check_ai_advisor() -> dict:
    """確認 AI 開團顧問建議筆數。"""
    t0 = time.monotonic()
    try:
        from app.models.ai_group_advice import AiGroupAdvice
        total = AiGroupAdvice.query.count()
        elapsed = time.monotonic() - t0
        if total == 0:
            return {"status": "WARNING", "response_time": elapsed,
                    "message": "尚無顧問建議，請執行重新計算"}
        return {"status": "HEALTHY", "response_time": elapsed,
                "message": f"顧問建議：{total} 筆"}
    except Exception as exc:
        return {"status": "ERROR", "response_time": time.monotonic() - t0,
                "message": str(exc)}


def check_crawler_coverage() -> dict:
    """確認爬蟲覆蓋率狀態。"""
    t0 = time.monotonic()
    try:
        from app.models.crawler_source_status import CrawlerSourceStatus
        total   = CrawlerSourceStatus.query.count()
        covered = CrawlerSourceStatus.query.filter(
            CrawlerSourceStatus.coverage_status.in_(["FULL", "PARTIAL"])
        ).count()
        elapsed = time.monotonic() - t0
        pct = int(covered / total * 100) if total else 0
        status = "HEALTHY" if pct >= 20 else "WARNING"
        return {"status": status, "response_time": elapsed,
                "message": f"來源覆蓋率 {pct}%（{covered}/{total}）"}
    except Exception as exc:
        return {"status": "ERROR", "response_time": time.monotonic() - t0,
                "message": str(exc)}


def check_storage() -> dict:
    """確認磁碟空間（簡易）。"""
    t0 = time.monotonic()
    try:
        import shutil
        total, used, free = shutil.disk_usage("/")
        elapsed = time.monotonic() - t0
        used_pct = int(used / total * 100)
        if used_pct >= 90:
            return {"status": "ERROR", "response_time": elapsed,
                    "message": f"磁碟空間嚴重不足（已用 {used_pct}%）"}
        elif used_pct >= 75:
            return {"status": "WARNING", "response_time": elapsed,
                    "message": f"磁碟空間偏高（已用 {used_pct}%）"}
        free_gb = free / (1024 ** 3)
        return {"status": "HEALTHY", "response_time": elapsed,
                "message": f"磁碟正常，剩餘 {free_gb:.1f} GB（已用 {used_pct}%）"}
    except Exception as exc:
        return {"status": "ERROR", "response_time": time.monotonic() - t0,
                "message": str(exc)}


# ── 尚未實作的模組 ─────────────────────────────────────────────────────────────

def _not_implemented(name: str) -> dict:
    return {"status": "NOT_IMPLEMENTED", "response_time": 0.0,
            "message": f"{name} 尚未實作，等待後續開發"}


def check_knowledge_center() -> dict:
    return _not_implemented("Knowledge Center")


def check_vector_search() -> dict:
    return _not_implemented("Vector Search")


def check_scheduler() -> dict:
    return _not_implemented("Scheduler")
