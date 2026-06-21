"""
crawler_coverage_service — 爬蟲資料覆蓋率分析服務。

對外介面：
  refresh()           → 刷新所有來源狀態（UPSERT crawler_source_status）
  get_coverage_data() → 回傳完整覆蓋率報告 dict
  get_gap_analysis()  → 回傳 concerts 資料庫 vs 來源 差異分析

來源清單與優先級：
  Priority 1（已有爬蟲）: KKTIX, TixCraft
  Priority 2（高價值）  : ibon, 寬宏
  Priority 3（中價值）  : 年代, Ticket Plus
  Priority 4（參考）    : udn售票網, Live Nation Taiwan, 高雄流行音樂中心, 台北流行音樂中心
"""
from __future__ import annotations

from datetime import datetime

# ── 來源定義 ──────────────────────────────────────────────────────────────────

ALL_SOURCES: list[dict] = [
    # Priority 1 — 已實作爬蟲
    {
        "key":          "kktix",
        "display_name": "KKTIX",
        "priority":     1,
        "crawler_key":  "kktix",
        "url":          "https://kktix.com",
        "notes":        "台灣最大售票平台，Playwright 爬蟲已完成",
        "value":        "HIGH",
    },
    {
        "key":          "tixcraft",
        "display_name": "TixCraft 拓元",
        "priority":     1,
        "crawler_key":  "tixcraft",
        "url":          "https://tixcraft.com",
        "notes":        "大型演唱會主要售票渠道，Playwright 爬蟲已完成",
        "value":        "HIGH",
    },
    # Priority 2 — 高價值，尚未實作
    {
        "key":          "ibon",
        "display_name": "ibon售票",
        "priority":     2,
        "crawler_key":  None,
        "url":          "https://ibon.com.tw",
        "notes":        "7-ELEVEN ibon，覆蓋中小型演唱會，動態 JS 頁面",
        "value":        "HIGH",
    },
    {
        "key":          "kham",
        "display_name": "寬宏藝術",
        "priority":     2,
        "crawler_key":  None,
        "url":          "https://www.kham.com.tw",
        "notes":        "台灣本土演唱會主辦，獨家場次多，靜態頁面較易爬取",
        "value":        "HIGH",
    },
    # Priority 3 — 中價值
    {
        "key":          "era",
        "display_name": "年代售票",
        "priority":     3,
        "crawler_key":  None,
        "url":          "https://ticket.era.com.tw",
        "notes":        "中型演唱會，部分獨家場次，需處理登入牆",
        "value":        "MEDIUM",
    },
    {
        "key":          "ticket_plus",
        "display_name": "Ticket Plus",
        "priority":     3,
        "crawler_key":  None,
        "url":          "https://www.ticket.com.tw",
        "notes":        "中華電信旗下售票，中小型活動為主",
        "value":        "MEDIUM",
    },
    # Priority 4 — 參考來源
    {
        "key":          "udn",
        "display_name": "udn售票網",
        "priority":     4,
        "crawler_key":  None,
        "url":          "https://ticket.udn.com",
        "notes":        "聯合報旗下，部分大型演唱會，資料量較少",
        "value":        "LOW",
    },
    {
        "key":          "live_nation",
        "display_name": "Live Nation Taiwan",
        "priority":     4,
        "crawler_key":  None,
        "url":          "https://www.livenation.com.tw",
        "notes":        "國際巡演為主（Taylor Swift、Coldplay 等），資料量稀但高價值",
        "value":        "HIGH",
    },
    {
        "key":          "kcmc",
        "display_name": "高雄流行音樂中心",
        "priority":     4,
        "crawler_key":  None,
        "url":          "https://www.kpmc.com.tw",
        "notes":        "高雄場館官網，海音館 / 表演廳，部分場次不上主流平台",
        "value":        "MEDIUM",
    },
    {
        "key":          "tpmc",
        "display_name": "台北流行音樂中心",
        "priority":     4,
        "crawler_key":  None,
        "url":          "https://tpmc.gov.taipei",
        "notes":        "台北場館官網，北流大舞台，部分場次不上主流平台",
        "value":        "MEDIUM",
    },
]

# 商機價值說明
_VALUE_LABELS = {"HIGH": "高", "MEDIUM": "中", "LOW": "低"}

# 預估開發時間（工作天）
_DEV_DAYS = {
    "kktix":       0,   # 已完成
    "tixcraft":    0,   # 已完成
    "ibon":        3,
    "kham":        2,
    "era":         4,
    "ticket_plus": 3,
    "udn":         3,
    "live_nation": 5,
    "kcmc":        4,
    "tpmc":        4,
}


# ── 主要服務 ──────────────────────────────────────────────────────────────────

def refresh() -> list[dict]:
    """
    刷新所有來源的 crawler_source_status 紀錄（UPSERT）。
    回傳完整報告 list。
    """
    from app import db
    from app.models.crawler_source_status import CrawlerSourceStatus
    from app.models.crawl_job import CrawlJob
    from sqlalchemy import func

    # 從 crawl_jobs 取最新執行資料（已實作的來源）
    job_stats: dict[str, dict] = {}
    rows = (
        db.session.query(
            CrawlJob.source_name,
            func.max(CrawlJob.finished_at).label("last_run"),
            func.sum(CrawlJob.created_count + CrawlJob.updated_count).label("imported"),
            func.sum(CrawlJob.skipped_count).label("skipped"),
        )
        .group_by(CrawlJob.source_name)
        .all()
    )
    for row in rows:
        # raw_count = 取最後一次 job 的 created+updated+skipped
        last_job = (
            CrawlJob.query
            .filter_by(source_name=row.source_name)
            .order_by(CrawlJob.finished_at.desc())
            .first()
        )
        raw = 0
        if last_job:
            raw = (last_job.created_count or 0) + (last_job.updated_count or 0) + (last_job.skipped_count or 0)
        job_stats[row.source_name] = {
            "last_run_at":    row.last_run,
            "imported_count": int(row.imported or 0),
            "skipped_count":  int(row.skipped or 0),
            "raw_count":      raw,
        }

    now = datetime.utcnow()
    existing = {s.source_name: s for s in CrawlerSourceStatus.query.all()}
    results = []

    for src in ALL_SOURCES:
        key          = src["key"]
        has_crawler  = src["crawler_key"] is not None
        stats        = job_stats.get(src["crawler_key"] or key, {})

        raw_count      = stats.get("raw_count", 0)
        imported_count = stats.get("imported_count", 0)
        skipped_count  = stats.get("skipped_count", 0)
        last_run_at    = stats.get("last_run_at")

        # 計算 coverage_status
        if not has_crawler:
            coverage_status = "NONE"
        elif imported_count >= raw_count > 0:
            coverage_status = "FULL"
        elif imported_count > 0:
            coverage_status = "PARTIAL"
        elif raw_count > 0:
            coverage_status = "PARTIAL"
        else:
            coverage_status = "NONE"

        # UPSERT
        rec = existing.get(key)
        if rec is None:
            rec = CrawlerSourceStatus(source_name=key, created_at=now)
            db.session.add(rec)

        rec.crawler_enabled = has_crawler
        rec.last_run_at     = last_run_at
        rec.raw_count       = raw_count
        rec.imported_count  = imported_count
        rec.skipped_count   = skipped_count
        rec.coverage_status = coverage_status
        rec.updated_at      = now

        results.append(_build_row(src, rec))

    db.session.commit()
    return results


def get_coverage_data() -> dict:
    """
    回傳完整覆蓋率報告，包含各來源狀態 + 統計摘要。
    """
    from app.models.crawler_source_status import CrawlerSourceStatus

    status_map = {s.source_name: s for s in CrawlerSourceStatus.query.all()}
    rows = []

    for src in ALL_SOURCES:
        rec = status_map.get(src["key"])
        rows.append(_build_row(src, rec))

    total    = len(rows)
    covered  = sum(1 for r in rows if r["coverage_status"] in ("FULL", "PARTIAL"))
    missing  = total - covered
    enabled  = sum(1 for r in rows if r["crawler_enabled"])

    return {
        "sources":      rows,
        "total":        total,
        "covered":      covered,
        "missing":      missing,
        "enabled":      enabled,
        "coverage_pct": int(covered / total * 100) if total else 0,
    }


def get_gap_analysis() -> dict:
    """
    concerts 資料表 vs 各來源差異分析。
    """
    from app import db
    from app.models.concert import Concert
    from sqlalchemy import func, text

    total_concerts = Concert.query.count()

    # 依 source_type 分群
    source_counts: dict[str, int] = {}
    rows = (
        db.session.query(Concert.source_type, func.count(Concert.id))
        .group_by(Concert.source_type)
        .all()
    )
    for row in rows:
        key = (row[0] or "UNKNOWN").upper()
        source_counts[key] = row[1]

    # 活動日期分佈
    upcoming = Concert.query.filter(
        Concert.concert_date >= datetime.utcnow().date()
    ).count() if _has_concert_date_col() else 0

    return {
        "total_concerts":   total_concerts,
        "source_breakdown": source_counts,
        "upcoming":         upcoming,
        "missing_sources":  [
            src["display_name"]
            for src in ALL_SOURCES
            if src["crawler_key"] is None
        ],
        "missing_count":    sum(
            1 for src in ALL_SOURCES if src["crawler_key"] is None
        ),
    }


def get_final_report() -> dict:
    """最終評估報告，供後台頁面渲染。"""
    completed   = [s for s in ALL_SOURCES if s["crawler_key"] is not None]
    pending     = [s for s in ALL_SOURCES if s["crawler_key"] is None]

    return {
        "completed": completed,
        "pending":   pending,
        "dev_days":  _DEV_DAYS,
        "value_labels": _VALUE_LABELS,
        "priority_groups": {
            1: [s for s in ALL_SOURCES if s["priority"] == 1],
            2: [s for s in ALL_SOURCES if s["priority"] == 2],
            3: [s for s in ALL_SOURCES if s["priority"] == 3],
            4: [s for s in ALL_SOURCES if s["priority"] == 4],
        },
        "next_recommended": _recommend_next(),
    }


# ── 內部工具 ──────────────────────────────────────────────────────────────────

def _build_row(src: dict, rec) -> dict:
    """組合單筆來源資料 dict（供模板渲染）。"""
    has_crawler = src["crawler_key"] is not None
    if rec:
        coverage_status = rec.coverage_status
        raw_count      = rec.raw_count
        imported_count = rec.imported_count
        skipped_count  = rec.skipped_count
        last_run_at    = rec.last_run_at
        coverage_pct   = rec.coverage_pct
    else:
        coverage_status = "NONE"
        raw_count = imported_count = skipped_count = coverage_pct = 0
        last_run_at = None

    return {
        "key":            src["key"],
        "source_name":    src["display_name"],
        "priority":       src["priority"],
        "crawler_enabled": has_crawler,
        "last_run_at":    last_run_at,
        "raw_count":      raw_count,
        "imported_count": imported_count,
        "skipped_count":  skipped_count,
        "coverage_status": coverage_status,
        "coverage_pct":   coverage_pct,
        "url":            src["url"],
        "notes":          src["notes"],
        "value":          src["value"],
        "dev_days":       _DEV_DAYS.get(src["key"], 3),
    }


def _recommend_next() -> dict:
    """建議下一個實作的來源。"""
    for src in ALL_SOURCES:
        if src["crawler_key"] is None and src["value"] == "HIGH":
            return {
                "key":  src["key"],
                "name": src["display_name"],
                "reason": f"Priority {src['priority']}、商機價值高、預估 {_DEV_DAYS.get(src['key'], 3)} 工作天",
            }
    return {}


def _has_concert_date_col() -> bool:
    try:
        from app.models.concert import Concert
        _ = Concert.concert_date
        return True
    except AttributeError:
        return False
