"""
concert_data_hub_service — Concert Data Hub 同步服務。

功能：
  sync_all()         從 concerts 表全量同步至 concert_data_hub
  rebuild()          先清空 concert_data_hub 再重建（完整重建）
  compute_score()    計算單筆 concert 的 confidence_score
  get_hub_stats()    回傳 Hub 統計（供 Dashboard 使用）

可信度計算規則（滿分 100）：
  KKTIX 來源    +40
  TixCraft 來源 +40
  日期不為空    +10
  場館非「待確認」 +10
"""
from __future__ import annotations

import json
from datetime import datetime


def compute_score(concert) -> int:
    """計算單筆 Concert 的可信度分數。"""
    score = 0
    source = (concert.source_type or "").upper()

    if "KKTIX" in source:
        score += 40
    if "TIXCRAFT" in source:
        score += 40
    if concert.concert_date is not None:
        score += 10
    if concert.venue and concert.venue not in ("待確認", "TBD", ""):
        score += 10

    return min(score, 100)


def sync_all() -> dict:
    """
    從 concerts 表同步所有資料至 concert_data_hub。
    已存在（concert_id 相同）→ UPDATE。
    不存在 → INSERT。
    回傳 {"created": N, "updated": N, "total": N}。
    """
    from app import db
    from app.models.concert import Concert
    from app.models.concert_data_hub import ConcertDataHub
    from app.services.concert_conflict_service import detect_conflicts_for

    concerts = Concert.query.all()
    created = updated = 0

    existing_map: dict[int, ConcertDataHub] = {
        h.concert_id: h
        for h in ConcertDataHub.query.filter(ConcertDataHub.concert_id.isnot(None)).all()
    }

    for c in concerts:
        score  = compute_score(c)
        source = (c.source_type or "").strip()
        count  = len([s for s in source.split(",") if s.strip()]) if source else 0

        conflicts    = detect_conflicts_for(c)
        has_conflict = len(conflicts) > 0
        conflict_str = ",".join(conflicts) if conflicts else None

        if c.id in existing_map:
            h = existing_map[c.id]
            h.artist_name      = c.artist
            h.concert_name     = c.name
            h.event_date       = c.concert_date
            h.venue            = c.venue
            h.city             = c.city
            h.source_count     = count
            h.source_types     = source
            h.source_urls      = c.source_urls
            h.confidence_score = score
            h.has_conflict     = has_conflict
            h.conflict_types   = conflict_str
            h.updated_at       = datetime.utcnow()
            updated += 1
        else:
            h = ConcertDataHub(
                concert_id       = c.id,
                artist_name      = c.artist,
                concert_name     = c.name,
                event_date       = c.concert_date,
                venue            = c.venue,
                city             = c.city,
                source_count     = count,
                source_types     = source,
                source_urls      = c.source_urls,
                confidence_score = score,
                has_conflict     = has_conflict,
                conflict_types   = conflict_str,
                status           = "active",
                created_at       = datetime.utcnow(),
                updated_at       = datetime.utcnow(),
            )
            db.session.add(h)
            created += 1

    db.session.commit()
    return {"created": created, "updated": updated, "total": created + updated}


def rebuild() -> dict:
    """
    完整重建 concert_data_hub。
    清空後重新從 concerts 同步所有資料。
    """
    from app import db
    from app.models.concert_data_hub import ConcertDataHub

    ConcertDataHub.query.delete()
    db.session.commit()
    return sync_all()


def get_hub_stats() -> dict:
    """
    回傳 Dashboard 需要的統計資料。
    """
    from app.models.concert_data_hub import ConcertDataHub

    total       = ConcertDataHub.query.filter_by(status="active").count()
    high_conf   = ConcertDataHub.query.filter(
        ConcertDataHub.status == "active",
        ConcertDataHub.confidence_score >= 80,
    ).count()
    conflicts   = ConcertDataHub.query.filter(
        ConcertDataHub.status == "active",
        ConcertDataHub.has_conflict == True,
    ).count()

    return {
        "total_concerts":    total,
        "high_confidence":   high_conf,
        "pending_conflicts": conflicts,
    }
