"""
BaseCrawler — 統一定義爬蟲介面。

子類別必須實作：
  fetch()  → list[dict]   取回原始資料列表
  parse()  → list[dict]   轉為標準化 concert dict
  save()   → (created, updated, skipped, errors)  寫入 concerts
"""
import hashlib
from abc import ABC, abstractmethod
from datetime import datetime, date

from app import db
from app.models.concert import Concert
from app.models.crawl_log import CrawlLog


class BaseCrawler(ABC):

    source_name: str = "base"

    def __init__(self, job_id: int):
        self.job_id = job_id

    # ── 必須由子類別實作 ──────────────────────────────────────────────────────

    @abstractmethod
    def fetch(self) -> list[dict]:
        """取回原始資料（HTTP / Mock）"""

    @abstractmethod
    def parse(self, raw: list[dict]) -> list[dict]:
        """
        將 fetch() 回傳值轉為標準 dict，每筆必須包含：
          artist      : str
          name        : str
          concert_date: date | None
          city        : str | None
          venue       : str | None
          status      : str  (預設 '評估中')
        """

    # ── 主流程 ────────────────────────────────────────────────────────────────

    def run(self) -> tuple[int, int, int, int]:
        """執行完整爬蟲流程，回傳 (created, updated, skipped, errors)"""
        raw = self.fetch()
        self._log("INFO", f"fetch() 取得 {len(raw)} 筆原始資料")

        records = self.parse(raw)
        self._log("INFO", f"parse() 解析出 {len(records)} 筆活動")

        created, updated, skipped, errors = self.save(records)
        self._log("INFO",
                  f"save() 完成：新增 {created} / 更新 {updated} / 跳過 {skipped} / 錯誤 {errors}")
        return created, updated, skipped, errors

    # ── 寫入邏輯（共用，子類別通常不需覆寫） ─────────────────────────────────

    def save(self, records: list[dict]) -> tuple[int, int, int, int]:
        created = updated = skipped = errors = 0

        for rec in records:
            try:
                h = self._make_hash(rec)
                existing = Concert.query.filter_by(crawler_hash=h).first()

                if existing:
                    # 更新資料
                    existing.artist       = rec.get("artist", existing.artist)
                    existing.name         = rec.get("name",   existing.name)
                    existing.concert_date = rec.get("concert_date", existing.concert_date)
                    existing.city         = rec.get("city",   existing.city)
                    existing.venue        = rec.get("venue",  existing.venue)
                    if rec.get("source_url"):
                        existing.source_url = rec["source_url"]
                    existing.updated_at   = datetime.utcnow()
                    updated += 1
                    self._log("INFO", f"[UPDATE] {rec.get('artist')} — {rec.get('name')}")
                else:
                    c = Concert(
                        artist       = rec["artist"],
                        name         = rec["name"],
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
                    self._log("INFO", f"[CREATE] {rec.get('artist')} — {rec.get('name')}")

            except Exception as exc:
                errors += 1
                self._log("ERROR", f"[ERROR] {rec}: {exc}")
                db.session.rollback()

        if created + updated > 0:
            db.session.commit()

        return created, updated, skipped, errors

    # ── 工具方法 ──────────────────────────────────────────────────────────────

    @staticmethod
    def _make_hash(rec: dict) -> str:
        """artist_name + event_date + venue 組合後 SHA256"""
        artist = (rec.get("artist") or "").strip().lower()
        date_str = str(rec.get("concert_date") or "")
        venue = (rec.get("venue") or "").strip().lower()
        raw = f"{artist}|{date_str}|{venue}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _log(self, level: str, message: str):
        entry = CrawlLog(
            job_id=self.job_id,
            source_name=self.source_name,
            level=level,
            message=message,
            created_at=datetime.utcnow(),
        )
        db.session.add(entry)
        try:
            db.session.flush()
        except Exception:
            db.session.rollback()
