"""
Concert Import Service

將標準化的爬蟲資料（list[dict]）寫入 concerts 資料表。

職責：
  - crawler_hash 去重（artist + event_date + venue → SHA256）
  - 新資料 → INSERT
  - 已存在 → UPDATE（避免重複建立）
  - 每筆獨立 try/except，單筆失敗不影響整批
  - 回傳 (created, updated, skipped, errors) 統計

使用方式：
    from app.services.concert_import_service import import_concerts
    created, updated, skipped, errors = import_concerts(records, job_id=job.id)
"""

import hashlib
from datetime import datetime
from typing import Optional

from app import db
from app.models.concert import Concert
from app.models.crawl_log import CrawlLog

# 去重 key 欄位
_HASH_FIELDS = ("artist", "concert_date", "venue")


def _make_hash(rec: dict) -> str:
    """
    以 artist + concert_date + venue 的組合產生 SHA256。
    與 BaseCrawler._make_hash() 演算法相同，確保一致性。
    """
    artist   = (rec.get("artist") or "").strip().lower()
    date_str = str(rec.get("concert_date") or "")
    venue    = (rec.get("venue")  or "").strip().lower()
    raw_str  = f"{artist}|{date_str}|{venue}"
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()


def _write_log(job_id: Optional[int], source_name: str, level: str, message: str):
    """寫入 crawl_logs，job_id 可為 None（獨立呼叫時）。"""
    if job_id is None:
        return
    entry = CrawlLog(
        job_id=job_id,
        source_name=source_name,
        level=level,
        message=message,
        created_at=datetime.utcnow(),
    )
    db.session.add(entry)
    try:
        db.session.flush()
    except Exception:
        db.session.rollback()


def import_concerts(
    records: list[dict],
    job_id: Optional[int] = None,
    source_name: str = "import",
) -> tuple[int, int, int, int]:
    """
    將標準化 concert dict 列表寫入 concerts 資料表。

    每筆 dict 應包含：
      artist        : str        必要
      name          : str        必要（演唱會名稱）
      concert_date  : date|None  可選
      city          : str|None   可選
      venue         : str|None   可選
      source_url    : str|None   可選
      status        : str        預設 '評估中'

    回傳 (created, updated, skipped, errors)。
    """
    created = updated = skipped = errors = 0

    for rec in records:
        try:
            artist = (rec.get("artist") or "").strip()
            name   = (rec.get("name")   or "").strip()

            if not artist or not name:
                skipped += 1
                _write_log(job_id, source_name, "WARNING",
                           f"[SKIP] 缺少 artist 或 name，略過：{rec}")
                continue

            h = _make_hash(rec)
            existing = Concert.query.filter_by(crawler_hash=h).first()

            if existing:
                # 更新既有資料
                existing.artist       = artist
                existing.name         = name
                existing.concert_date = rec.get("concert_date", existing.concert_date)
                existing.city         = rec.get("city",   existing.city)
                existing.venue        = rec.get("venue",  existing.venue)
                if rec.get("source_url"):
                    existing.source_url = rec["source_url"]
                existing.updated_at   = datetime.utcnow()
                updated += 1
                _write_log(job_id, source_name, "INFO",
                           f"[UPDATE] {artist} — {name}")
            else:
                # 新增
                c = Concert(
                    artist       = artist,
                    name         = name,
                    concert_date = rec.get("concert_date"),
                    city         = rec.get("city"),
                    venue        = rec.get("venue"),
                    source_url   = rec.get("source_url"),
                    status       = rec.get("status", "評估中"),
                    crawler_hash = h,
                    created_at   = datetime.utcnow(),
                    updated_at   = datetime.utcnow(),
                )
                db.session.add(c)
                created += 1
                _write_log(job_id, source_name, "INFO",
                           f"[CREATE] {artist} — {name}")

        except Exception as exc:
            errors += 1
            _write_log(job_id, source_name, "ERROR",
                       f"[ERROR] {rec}: {exc}")
            db.session.rollback()

    if created + updated > 0:
        try:
            db.session.commit()
        except Exception as exc:
            errors += 1
            db.session.rollback()
            _write_log(job_id, source_name, "ERROR",
                       f"[COMMIT ERROR] {exc}")

    return created, updated, skipped, errors
