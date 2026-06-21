"""
risk_advisor — 風險評估引擎（Rule-Based）。

整合 BusinessInsight.risk_level + confidence_score 計算最終建議風險。

信心分數（0–100）計算：
  基礎：opportunity_score（最多 50 分）
  來源數：雙來源 +20 / 單來源 +10
  歷史紀錄：有歷史資料 +20
  日期確認：日期已知 +10
"""
from __future__ import annotations


def assess_risk(hub, bi) -> str:
    """
    回傳 'LOW' / 'MEDIUM' / 'HIGH'。

    hub : ConcertDataHub
    bi  : BusinessInsight（可為 None）
    """
    if bi is None:
        return "HIGH"

    return bi.risk_level


def compute_confidence_score(hub, bi) -> int:
    """
    計算顧問信心分數（0–100）。

    綜合 BI opportunity_score + 資料來源 + 歷史紀錄 + 日期確認。
    """
    score = 0

    # 1. Opportunity score 佔 50%
    if bi:
        score += int(bi.opportunity_score * 0.50)

    # 2. 來源數
    source_count = hub.source_count or 0
    if source_count >= 2:
        score += 20
    elif source_count == 1:
        score += 10

    # 3. 有歷史訂單資料
    if _has_history(hub.artist_name):
        score += 20

    # 4. 日期已確認
    if hub.event_date:
        score += 10

    return min(score, 100)


def _has_history(artist_name: str) -> bool:
    """確認是否有同藝人的歷史 EventPage（已發布過）。"""
    try:
        from app.models.event_page import EventPage
        return (
            EventPage.query
            .filter(
                EventPage.deleted_at.is_(None),
                EventPage.status.in_(["已發布", "完成"]),
                EventPage.artist_name.ilike(f"%{artist_name}%"),
            )
            .first() is not None
        )
    except Exception:
        return False
