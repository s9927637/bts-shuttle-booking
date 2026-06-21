"""
Crawler Diagnostics Service

分析爬蟲各階段資料流失原因，提供診斷報告。

不修改任何爬蟲邏輯，只做觀測與分析。
"""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, datetime

from sqlalchemy import func

from app import db
from app.models.concert import Concert
from app.models.crawl_job import CrawlJob
from app.models.crawl_log import CrawlLog


# ── 常數 ─────────────────────────────────────────────────────────────────────

SOURCES = ["kktix", "tixcraft", "mock"]

# Skip 原因分類（從 log message 解析）
_SKIP_PATTERNS: list[tuple[str, str]] = [
    (r"活動日期不可空白",     "event_date_missing"),
    (r"活動名稱不可空白",     "name_missing"),
    (r"活動名稱過短",         "name_too_short"),
    (r"crawler_hash.*unique", "duplicate_hash"),
    (r"重複",                  "duplicate"),
    (r"past.*event|過去活動",  "past_event"),
    (r"invalid_format|格式錯誤","invalid_format"),
    (r"venue.*missing|場館",   "venue_missing"),
    (r"artist.*missing|藝人",  "artist_missing"),
]


def _classify_skip_reason(message: str) -> str:
    """從 log message 分類 skip 原因。"""
    for pattern, label in _SKIP_PATTERNS:
        if re.search(pattern, message, re.IGNORECASE):
            return label
    return "other"


# ── 爬蟲日誌解析 ─────────────────────────────────────────────────────────────

def _parse_job_logs(job: CrawlJob) -> dict:
    """從單一 CrawlJob 的 logs 解析 fetch/parse/save 各階段數字。"""
    raw_count    = None
    parsed_count = None
    created      = job.created_count
    updated      = job.updated_count
    skipped      = job.skipped_count
    errors       = job.error_count
    skip_reasons: dict[str, int] = defaultdict(int)

    for log in job.logs:
        msg = log.message

        # fetch 取得
        m = re.search(r"fetch\(\) 取得 (\d+) 筆", msg)
        if m:
            raw_count = int(m.group(1))

        # parse 解析
        m = re.search(r"parse\(\) 解析出 (\d+) 筆", msg)
        if m:
            parsed_count = int(m.group(1))

        # SKIP log
        if "[SKIP]" in msg or log.level == "WARNING" and "略過" in msg:
            reason = _classify_skip_reason(msg)
            skip_reasons[reason] += 1

    imported = created + updated
    return {
        "raw_count":    raw_count,
        "parsed_count": parsed_count,
        "imported":     imported,
        "created":      created,
        "updated":      updated,
        "skipped":      skipped,
        "errors":       errors,
        "skip_reasons": dict(skip_reasons),
    }


# ── 主診斷函式 ────────────────────────────────────────────────────────────────

def get_source_diagnostics() -> list[dict]:
    """
    每個來源的最新爬蟲診斷：
    raw / parsed / imported / skipped / skip_reasons / last_ran_at
    """
    results = []
    for source in SOURCES:
        # 最近 10 筆 jobs
        jobs = (
            CrawlJob.query
            .filter_by(source_name=source)
            .order_by(CrawlJob.created_at.desc())
            .limit(10)
            .options(db.joinedload(CrawlJob.logs))
            .all()
        )

        last_job = jobs[0] if jobs else None
        last_stats = _parse_job_logs(last_job) if last_job else {}

        # 歷史累計
        total_created = sum(j.created_count for j in jobs)
        total_updated = sum(j.updated_count for j in jobs)
        total_skipped = sum(j.skipped_count for j in jobs)
        total_errors  = sum(j.error_count   for j in jobs)

        # 累計 skip 原因
        agg_skip: dict[str, int] = defaultdict(int)
        for j in jobs:
            parsed = _parse_job_logs(j)
            for reason, cnt in parsed.get("skip_reasons", {}).items():
                agg_skip[reason] += cnt

        # DB 中來源對應的演唱會
        q = Concert.query
        if source == "kktix":
            q = q.filter(Concert.source_url.ilike("%kktix%"))
        elif source == "tixcraft":
            q = q.filter(Concert.source_type == "TIXCRAFT")
        elif source == "mock":
            q = q.filter(Concert.source_type.is_(None))
        db_count = q.count()

        results.append({
            "source":        source,
            "last_job_id":   last_job.id if last_job else None,
            "last_status":   last_job.status if last_job else "never",
            "last_ran_at":   last_job.created_at if last_job else None,
            "last_raw":      last_stats.get("raw_count"),
            "last_parsed":   last_stats.get("parsed_count"),
            "last_imported": last_stats.get("imported", 0),
            "last_skipped":  last_stats.get("skipped", 0),
            "total_created": total_created,
            "total_updated": total_updated,
            "total_skipped": total_skipped,
            "total_errors":  total_errors,
            "db_count":      db_count,
            "skip_reasons":  dict(agg_skip),
            "jobs":          jobs,
        })

    return results


def get_skip_reason_stats() -> list[dict]:
    """
    從所有爬蟲 logs 彙整 skip 原因排行（Top 20）。
    """
    skip_logs = (
        CrawlLog.query
        .filter(
            db.or_(
                CrawlLog.message.contains("[SKIP]"),
                db.and_(
                    CrawlLog.level == "WARNING",
                    CrawlLog.message.contains("略過"),
                )
            )
        )
        .all()
    )

    reason_counts: dict[str, int] = defaultdict(int)
    reason_examples: dict[str, list[str]] = defaultdict(list)

    for log in skip_logs:
        reason = _classify_skip_reason(log.message)
        reason_counts[reason] += 1
        if len(reason_examples[reason]) < 3:
            reason_examples[reason].append(log.message[:120])

    result = sorted(
        [
            {
                "reason":   reason,
                "count":    count,
                "examples": reason_examples[reason],
            }
            for reason, count in reason_counts.items()
        ],
        key=lambda x: x["count"],
        reverse=True,
    )[:20]

    return result


def get_date_distribution() -> dict:
    """演唱會日期分布統計。"""
    today = date.today()
    year  = today.year

    total  = Concert.query.count()
    future = Concert.query.filter(Concert.concert_date >= today).count()
    past   = Concert.query.filter(Concert.concert_date < today).count()
    no_date = Concert.query.filter(Concert.concert_date.is_(None)).count()
    this_year = Concert.query.filter(
        Concert.concert_date >= date(year, 1, 1),
        Concert.concert_date <= date(year, 12, 31),
    ).count()
    last_year = Concert.query.filter(
        Concert.concert_date >= date(year - 1, 1, 1),
        Concert.concert_date <= date(year - 1, 12, 31),
    ).count()
    next_year = Concert.query.filter(
        Concert.concert_date >= date(year + 1, 1, 1),
        Concert.concert_date <= date(year + 1, 12, 31),
    ).count()

    return {
        "total":      total,
        "future":     future,
        "past":       past,
        "no_date":    no_date,
        "this_year":  this_year,
        "last_year":  last_year,
        "next_year":  next_year,
    }


def get_recent_concerts(limit: int = 100) -> list[Concert]:
    """最近匯入的前 N 筆演唱會。"""
    return (
        Concert.query
        .order_by(Concert.created_at.desc())
        .limit(limit)
        .all()
    )


def get_future_concerts(limit: int = 50) -> list[Concert]:
    """未來演唱會（concert_date >= today），依日期排序。"""
    today = date.today()
    return (
        Concert.query
        .filter(Concert.concert_date >= today)
        .order_by(Concert.concert_date.asc())
        .limit(limit)
        .all()
    )


def get_crawl_jobs_summary(limit: int = 30) -> list[dict]:
    """最近爬蟲 job 摘要列表，帶解析後的各階段數字。"""
    jobs = (
        CrawlJob.query
        .order_by(CrawlJob.created_at.desc())
        .limit(limit)
        .options(db.joinedload(CrawlJob.logs))
        .all()
    )

    result = []
    for job in jobs:
        stats = _parse_job_logs(job)
        result.append({
            "id":          job.id,
            "source":      job.source_name,
            "status":      job.status,
            "ran_at":      job.created_at,
            "duration_s":  job.duration_seconds,
            "raw":         stats.get("raw_count"),
            "parsed":      stats.get("parsed_count"),
            "created":     stats.get("created", 0),
            "updated":     stats.get("updated", 0),
            "skipped":     stats.get("skipped", 0),
            "errors":      stats.get("errors", 0),
            "skip_reasons": stats.get("skip_reasons", {}),
        })
    return result


def get_pipeline_diagnosis() -> dict:
    """
    完整流水線診斷：找出在哪個階段資料遺失。
    回傳各來源：fetch_count → parse_count → imported_count 的漏斗。
    """
    source_diag = get_source_diagnostics()
    diagnosis = []
    for s in source_diag:
        raw      = s["last_raw"] or 0
        parsed   = s["last_parsed"] or 0
        imported = s["last_imported"] or 0
        skipped  = s["last_skipped"] or 0

        # 計算各階段遺失
        fetch_to_parse_loss   = max(0, raw - parsed)
        parse_to_import_loss  = max(0, parsed - imported - skipped)
        skip_loss             = skipped

        # 診斷結論
        issues = []
        if raw == 0:
            issues.append("⚠️ FETCH 層取不到資料（頁面無法載入或選取器失效）")
        elif raw < 10:
            issues.append(f"⚠️ FETCH 層資料量偏低（{raw} 筆），可能需要分頁/捲動")
        if fetch_to_parse_loss > 0:
            issues.append(f"⚠️ PARSE 階段遺失 {fetch_to_parse_loss} 筆（日期/格式解析失敗）")
        if skip_loss > 0:
            issues.append(f"⚠️ VALIDATE 階段 SKIP {skip_loss} 筆")
        if parse_to_import_loss > 0:
            issues.append(f"⚠️ SAVE 階段遺失 {parse_to_import_loss} 筆（可能重複或錯誤）")

        diagnosis.append({
            "source":              s["source"],
            "fetch_count":         raw,
            "parse_count":         parsed,
            "imported_count":      imported,
            "skipped_count":       skipped,
            "fetch_parse_loss":    fetch_to_parse_loss,
            "parse_import_loss":   parse_to_import_loss,
            "db_total":            s["db_count"],
            "issues":              issues,
            "skip_reasons":        s["skip_reasons"],
            "last_ran_at":         s["last_ran_at"],
            "last_status":         s["last_status"],
        })

    return {
        "sources":  diagnosis,
        "db_dist":  get_date_distribution(),
        "top_skip": get_skip_reason_stats(),
    }


def get_top_missing_events(limit: int = 50) -> list[dict]:
    """
    未來演唱會列表（可能是應抓到卻未抓到的活動）。
    這裡列出 DB 中的未來活動，供人工比對。
    """
    today = date.today()
    concerts = (
        Concert.query
        .filter(Concert.concert_date >= today)
        .order_by(Concert.concert_date.asc())
        .limit(limit)
        .all()
    )
    result = []
    for c in concerts:
        result.append({
            "id":           c.id,
            "artist":       c.artist,
            "name":         c.name,
            "concert_date": c.concert_date,
            "city":         c.city,
            "venue":        c.venue,
            "source_type":  c.source_type,
            "source_url":   c.source_url,
        })
    return result


def generate_diagnostics_report() -> dict:
    """
    完整診斷報告：供 /admin/crawlers/debug 頁面使用。
    """
    pipeline   = get_pipeline_diagnosis()
    recent_100 = get_recent_concerts(100)
    future_50  = get_future_concerts(50)
    jobs_summary = get_crawl_jobs_summary(30)

    return {
        "pipeline":       pipeline,
        "recent_concerts": recent_100,
        "future_concerts": future_50,
        "jobs_summary":    jobs_summary,
        "generated_at":    datetime.utcnow(),
    }
