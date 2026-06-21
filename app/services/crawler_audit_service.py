"""
Crawler Audit Service

分析 crawler_audit_logs 表，提供：
- Future Event 列表
- Missing Event（SKIPPED）列表
- Coverage 統計
- Skip Reason Top 20
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime

from sqlalchemy import func

from app import db
from app.models.crawler_audit_log import CrawlerAuditLog
from app.models.concert import Concert
from app.models.crawl_job import CrawlJob


SOURCES = ["kktix", "tixcraft", "mock"]


# ── 統計摘要 ──────────────────────────────────────────────────────────────────

def get_audit_summary() -> dict:
    """所有來源的 audit 統計（可放 Dashboard）。"""
    today = date.today()

    total_imported = CrawlerAuditLog.query.filter_by(status="IMPORTED").count()
    total_skipped  = CrawlerAuditLog.query.filter_by(status="SKIPPED").count()
    past_event     = CrawlerAuditLog.query.filter_by(
        status="SKIPPED", reason="PAST_EVENT"
    ).count()

    future_in_db = Concert.query.filter(
        Concert.concert_date >= today
    ).count()

    pending_validated = CrawlerAuditLog.query.filter_by(
        status="VALIDATED"
    ).count()

    return {
        "total_imported":   total_imported,
        "total_skipped":    total_skipped,
        "past_event_skips": past_event,
        "future_in_db":     future_in_db,
        "pending_validated": pending_validated,
    }


# ── Coverage 分析 ─────────────────────────────────────────────────────────────

def get_coverage_by_source() -> list[dict]:
    """每個來源的 IMPORTED / SKIPPED 統計。"""
    rows = (
        db.session.query(
            CrawlerAuditLog.source_name,
            CrawlerAuditLog.status,
            func.count(CrawlerAuditLog.id).label("cnt"),
        )
        .group_by(CrawlerAuditLog.source_name, CrawlerAuditLog.status)
        .all()
    )

    coverage: dict[str, dict] = defaultdict(
        lambda: {"imported": 0, "skipped": 0, "total": 0}
    )
    for row in rows:
        src = row.source_name
        coverage[src]["total"] += row.cnt
        if row.status == "IMPORTED":
            coverage[src]["imported"] += row.cnt
        elif row.status == "SKIPPED":
            coverage[src]["skipped"] += row.cnt

    result = []
    for source in SOURCES:
        d = coverage.get(source, {"imported": 0, "skipped": 0, "total": 0})
        total = d["total"] or 1
        result.append({
            "source":        source,
            "imported":      d["imported"],
            "skipped":       d["skipped"],
            "total":         d["total"],
            "coverage_pct":  round(d["imported"] / total * 100, 1),
        })
    return result


# ── Future Events ─────────────────────────────────────────────────────────────

def get_future_events(page: int = 1, per_page: int = 50) -> dict:
    """
    IMPORTED 且 event_date >= today 的活動（分頁）。
    """
    today = date.today()
    query = (
        CrawlerAuditLog.query
        .filter(
            CrawlerAuditLog.status == "IMPORTED",
            CrawlerAuditLog.event_date >= today,
        )
        .order_by(CrawlerAuditLog.event_date.asc())
    )
    total = query.count()
    pages = max(1, (total + per_page - 1) // per_page)
    page  = min(page, pages)
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return {"items": items, "total": total, "page": page, "pages": pages}


# ── Missing Events（SKIPPED）────────────────────────────────────────────────

def get_missing_events(
    reason_filter: str = "",
    page: int = 1,
    per_page: int = 50,
) -> dict:
    """SKIPPED 的活動，可依 reason 過濾。"""
    query = CrawlerAuditLog.query.filter_by(status="SKIPPED")
    if reason_filter:
        query = query.filter_by(reason=reason_filter)
    query = query.order_by(CrawlerAuditLog.created_at.desc())

    total = query.count()
    pages = max(1, (total + per_page - 1) // per_page)
    page  = min(page, pages)
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return {"items": items, "total": total, "page": page, "pages": pages}


# ── Skip Reason Top 20 ────────────────────────────────────────────────────────

def get_skip_reasons(limit: int = 20) -> list[dict]:
    rows = (
        db.session.query(
            CrawlerAuditLog.reason,
            func.count(CrawlerAuditLog.id).label("cnt"),
        )
        .filter(CrawlerAuditLog.status == "SKIPPED")
        .group_by(CrawlerAuditLog.reason)
        .order_by(func.count(CrawlerAuditLog.id).desc())
        .limit(limit)
        .all()
    )
    reason_labels = {
        "DATE_MISSING":   "缺少日期",
        "ARTIST_MISSING": "缺少藝人",
        "VENUE_MISSING":  "缺少場館",
        "PAST_EVENT":     "歷史活動",
        "DUPLICATE":      "重複資料",
        "INVALID_FORMAT": "格式錯誤",
        "IMPORT_ERROR":   "匯入錯誤",
    }
    return [
        {
            "reason":  row.reason or "UNKNOWN",
            "label":   reason_labels.get(row.reason or "", row.reason or "未知"),
            "count":   row.cnt,
        }
        for row in rows
    ]


# ── All Audit Logs（for /api/crawlers/audit）─────────────────────────────────

def get_audit_logs(
    source: str = "",
    status: str = "",
    page: int = 1,
    per_page: int = 50,
) -> dict:
    query = CrawlerAuditLog.query
    if source:
        query = query.filter_by(source_name=source)
    if status:
        query = query.filter_by(status=status)
    query = query.order_by(CrawlerAuditLog.created_at.desc())

    total = query.count()
    pages = max(1, (total + per_page - 1) // per_page)
    page  = min(page, pages)
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return {"items": items, "total": total, "page": page, "pages": pages}


# ── 最近 Job 的 audit 摘要 ────────────────────────────────────────────────────

def get_last_job_audit(source_name: str) -> dict:
    """最近一次爬蟲 job 的 audit 摘要。"""
    last_job = (
        CrawlJob.query
        .filter_by(source_name=source_name)
        .order_by(CrawlJob.created_at.desc())
        .first()
    )
    if not last_job:
        return {"job_id": None, "imported": 0, "skipped": 0, "past_event": 0}

    job_id = last_job.id
    imported   = CrawlerAuditLog.query.filter_by(job_id=job_id, status="IMPORTED").count()
    skipped    = CrawlerAuditLog.query.filter_by(job_id=job_id, status="SKIPPED").count()
    past_event = CrawlerAuditLog.query.filter_by(
        job_id=job_id, status="SKIPPED", reason="PAST_EVENT"
    ).count()

    return {
        "job_id":     job_id,
        "ran_at":     last_job.created_at,
        "imported":   imported,
        "skipped":    skipped,
        "past_event": past_event,
    }
