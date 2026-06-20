"""
CrawlerManager — 統一管理各爬蟲的執行入口。

支援：
  run_mock()     執行 MockCrawler（測試用）
  run_kktix()    執行 KKTixCrawler
  run_tixcraft() 執行 TixCraftCrawler
  run_all()      依序執行 kktix + tixcraft
"""
from datetime import datetime
from typing import Optional

from app import db
from app.models.crawl_job import CrawlJob


def _run_source(source_name: str) -> dict:
    """
    建立 CrawlJob → 執行爬蟲 → 更新 Job 狀態。
    回傳結果 dict。
    """
    from app.services.crawlers import REGISTRY

    if source_name not in REGISTRY:
        raise ValueError(f"未知來源：{source_name}")

    job = CrawlJob(
        source_name=source_name,
        status="running",
        started_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
    )
    db.session.add(job)
    db.session.commit()

    try:
        crawler_cls = REGISTRY[source_name]
        crawler     = crawler_cls(job_id=job.id)
        created, updated, skipped, errors = crawler.run()

        job.status        = "success" if errors == 0 else "partial"
        job.finished_at   = datetime.utcnow()
        job.created_count = created
        job.updated_count = updated
        job.skipped_count = skipped
        job.error_count   = errors
        if errors == 0:
            job.last_success_at = datetime.utcnow()
        db.session.commit()

    except Exception as exc:
        job.status      = "error"
        job.finished_at = datetime.utcnow()
        job.error_count = (job.error_count or 0) + 1
        db.session.commit()
        raise

    return {
        "job_id":   job.id,
        "source":   source_name,
        "status":   job.status,
        "created":  job.created_count,
        "updated":  job.updated_count,
        "skipped":  job.skipped_count,
        "errors":   job.error_count,
        "duration": job.duration_seconds,
    }


def run_mock() -> dict:
    return _run_source("mock")


def run_kktix() -> dict:
    return _run_source("kktix")


def run_tixcraft() -> dict:
    return _run_source("tixcraft")


def run_all() -> list[dict]:
    """
    依序執行 kktix + tixcraft。
    一個失敗不影響下一個。
    """
    results = []
    for source in ["kktix", "tixcraft"]:
        try:
            result = _run_source(source)
        except Exception as exc:
            result = {
                "source":  source,
                "status":  "error",
                "error":   str(exc),
            }
        results.append(result)
    return results
