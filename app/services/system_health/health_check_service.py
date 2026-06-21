"""
health_check_service — 系統健康度主控服務。

對外介面：
  run_all()         → list[dict]  執行所有檢查，UPSERT DB，回傳結果
  get_summary()     → dict        Dashboard 統計
  get_all_results() → list[dict]  讀取 DB 現有結果（不重新執行）

元件清單（有序）：
  database, crawler, concert_hub, business_intelligence,
  ai_advisor, crawler_coverage, storage,
  knowledge_center, vector_search, scheduler
"""
from __future__ import annotations

from datetime import datetime

# ── 元件登錄表 ────────────────────────────────────────────────────────────────

COMPONENTS: list[dict] = [
    {"key": "database",             "display": "Database",            "category": "核心"},
    {"key": "crawler",              "display": "Crawler",             "category": "資料收集"},
    {"key": "concert_hub",          "display": "Concert Hub",         "category": "資料收集"},
    {"key": "crawler_coverage",     "display": "Crawler Coverage",    "category": "資料收集"},
    {"key": "business_intelligence","display": "Business Intelligence","category": "商機決策"},
    {"key": "ai_advisor",           "display": "AI Group Advisor",    "category": "商機決策"},
    {"key": "storage",              "display": "Storage",             "category": "基礎設施"},
    {"key": "knowledge_center",     "display": "Knowledge Center",    "category": "未實作"},
    {"key": "vector_search",        "display": "Vector Search",       "category": "未實作"},
    {"key": "scheduler",            "display": "Scheduler",           "category": "未實作"},
]

_CHECKER_MAP = {
    "database":              "check_database",
    "crawler":               "check_crawler",
    "concert_hub":           "check_concert_hub",
    "business_intelligence": "check_business_intelligence",
    "ai_advisor":            "check_ai_advisor",
    "crawler_coverage":      "check_crawler_coverage",
    "storage":               "check_storage",
    "knowledge_center":      "check_knowledge_center",
    "vector_search":         "check_vector_search",
    "scheduler":             "check_scheduler",
}


# ── 主要服務 ──────────────────────────────────────────────────────────────────

def run_all() -> list[dict]:
    """執行所有健康檢查，UPSERT system_health_checks，回傳完整結果。"""
    from app import db
    from app.models.system_health_check import SystemHealthCheck
    import app.services.system_health.component_checker as cc

    now      = datetime.utcnow()
    existing = {r.component_name: r for r in SystemHealthCheck.query.all()}
    results  = []

    for comp in COMPONENTS:
        key          = comp["key"]
        checker_name = _CHECKER_MAP.get(key)
        checker_fn   = getattr(cc, checker_name, None) if checker_name else None

        if checker_fn:
            result = checker_fn()
        else:
            result = {"status": "UNKNOWN", "response_time": 0.0, "message": "無檢查器"}

        rec = existing.get(key)
        if rec is None:
            rec = SystemHealthCheck(component_name=key, created_at=now)
            db.session.add(rec)

        rec.status          = result["status"]
        rec.response_time   = result.get("response_time")
        rec.last_checked_at = now
        rec.message         = result.get("message", "")

        results.append(_build_row(comp, rec))

    db.session.commit()
    return results


def get_all_results() -> list[dict]:
    """讀取 DB 現有結果（不重新執行）。若無紀錄則回傳預設值。"""
    from app.models.system_health_check import SystemHealthCheck
    existing = {r.component_name: r for r in SystemHealthCheck.query.all()}

    rows = []
    for comp in COMPONENTS:
        rec = existing.get(comp["key"])
        rows.append(_build_row(comp, rec))
    return rows


def get_summary() -> dict:
    """Dashboard 統計用。"""
    rows = get_all_results()
    healthy  = sum(1 for r in rows if r["status"] == "HEALTHY")
    warning  = sum(1 for r in rows if r["status"] == "WARNING")
    error    = sum(1 for r in rows if r["status"] == "ERROR")
    unknown  = sum(1 for r in rows if r["status"] in ("NOT_IMPLEMENTED", "UNKNOWN"))
    total    = len(rows)
    return {
        "total":   total,
        "healthy": healthy,
        "warning": warning,
        "error":   error,
        "unknown": unknown,
        "overall": _overall_status(healthy, warning, error, total - unknown),
    }


# ── 內部工具 ──────────────────────────────────────────────────────────────────

def _build_row(comp: dict, rec) -> dict:
    if rec:
        return {
            "key":            comp["key"],
            "display":        comp["display"],
            "category":       comp["category"],
            "status":         rec.status,
            "status_label":   rec.status_label,
            "status_color":   rec.status_color,
            "response_time":  rec.response_time,
            "response_ms":    rec.response_time_ms,
            "last_checked_at":rec.last_checked_at,
            "message":        rec.message or "",
        }
    return {
        "key":            comp["key"],
        "display":        comp["display"],
        "category":       comp["category"],
        "status":         "UNKNOWN",
        "status_label":   "未知",
        "status_color":   "gray",
        "response_time":  None,
        "response_ms":    "—",
        "last_checked_at":None,
        "message":        "尚未執行檢查",
    }


def _overall_status(healthy: int, warning: int, error: int, active: int) -> str:
    if error > 0:
        return "ERROR"
    if warning > 0:
        return "WARNING"
    if healthy == active and active > 0:
        return "HEALTHY"
    return "UNKNOWN"
