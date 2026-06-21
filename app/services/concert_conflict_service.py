"""
concert_conflict_service — 演唱會資料衝突檢查服務。

衝突類型：
  venue_missing    場館未填（待確認）
  city_missing     城市未填（待確認）
  date_missing     日期未填
  date_near_dup    同藝人在 7 天內有另一場演出（疑似重複或多場）
"""
from __future__ import annotations

from datetime import timedelta


def detect_conflicts_for(concert) -> list[str]:
    """
    檢查單筆 concert 的衝突類型。
    回傳衝突類型列表（空 list = 無衝突）。
    """
    from app.models.concert import Concert

    issues: list[str] = []

    if not concert.venue or concert.venue in ("待確認", "TBD", ""):
        issues.append("venue_missing")

    if not concert.city or concert.city in ("待確認", "TBD", ""):
        issues.append("city_missing")

    if concert.concert_date is None:
        issues.append("date_missing")
    else:
        # 檢查同藝人 7 天內是否有其他場次（疑似重複）
        nearby = (
            Concert.query
            .filter(
                Concert.artist == concert.artist,
                Concert.id != concert.id,
                Concert.concert_date >= concert.concert_date - timedelta(days=7),
                Concert.concert_date <= concert.concert_date + timedelta(days=7),
            )
            .first()
        )
        if nearby:
            issues.append("date_near_dup")

    return issues


def get_all_conflicts() -> list[dict]:
    """
    回傳所有有衝突的 Hub 資料，附帶建議修正說明。
    """
    from app.models.concert_data_hub import ConcertDataHub

    rows = (
        ConcertDataHub.query
        .filter(
            ConcertDataHub.status == "active",
            ConcertDataHub.has_conflict == True,
        )
        .order_by(ConcertDataHub.confidence_score.asc())
        .all()
    )

    result = []
    for h in rows:
        conflict_types = (h.conflict_types or "").split(",")
        suggestions    = _build_suggestions(conflict_types)
        result.append({
            "id":              h.id,
            "concert_id":      h.concert_id,
            "artist_name":     h.artist_name,
            "concert_name":    h.concert_name,
            "event_date":      str(h.event_date) if h.event_date else None,
            "source_types":    h.source_types,
            "conflict_types":  conflict_types,
            "suggestions":     suggestions,
            "confidence_score": h.confidence_score,
        })
    return result


def _build_suggestions(conflict_types: list[str]) -> list[str]:
    """根據衝突類型產生建議修正文字。"""
    suggestions = []
    _MAP = {
        "venue_missing":  "場館未填，請手動補充場館名稱",
        "city_missing":   "城市未填，請確認活動舉辦城市",
        "date_missing":   "日期未填，請確認活動日期",
        "date_near_dup":  "同藝人 7 天內有其他場次，請確認是否為重複資料",
    }
    for ct in conflict_types:
        ct = ct.strip()
        if ct and ct in _MAP:
            suggestions.append(_MAP[ct])
    return suggestions


_CONFLICT_TYPE_LABELS = {
    "venue_missing":  "場館未填",
    "city_missing":   "城市未填",
    "date_missing":   "日期未填",
    "date_near_dup":  "日期近似重複",
}


def conflict_label(conflict_type: str) -> str:
    return _CONFLICT_TYPE_LABELS.get(conflict_type.strip(), conflict_type)
