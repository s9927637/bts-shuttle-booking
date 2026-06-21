"""
city_advisor — 出發城市建議引擎（Rule-Based）。

優先順序：
  1. hub.city（活動所在城市）→ 若明確且在清單內直接推薦
  2. 同藝人歷史 EventPage 出發城市（取最多次）
  3. 依商機分數城市預設
  4. fallback → 台北
"""
from __future__ import annotations

from collections import Counter

_VALID_CITIES = ["台北", "新北", "桃園", "新竹", "台中", "台南", "高雄"]

_BI_CITY_MAP = {
    "高雄": ["高雄", "台南"],
    "台南": ["台南", "高雄"],
    "台中": ["台中", "桃園"],
    "台北": ["台北", "桃園"],
}


def recommend_departure_city(hub, bi) -> str:
    """
    回傳建議出發城市（單一城市）。

    hub : ConcertDataHub
    bi  : BusinessInsight（可為 None）
    """
    event_city = (hub.city or "").strip()

    # 若活動城市已明確在清單內 → 直接推薦該城市（就近出發）
    if event_city in _VALID_CITIES:
        return event_city

    # 查歷史紀錄
    hist = _historical_departure_city(hub.artist_name)
    if hist:
        return hist

    # 依 BI 城市映射
    if event_city in _BI_CITY_MAP:
        return _BI_CITY_MAP[event_city][0]

    return "台北"


def recommend_all_cities(hub) -> list[str]:
    """回傳所有建議出發城市（含多個）。"""
    event_city = (hub.city or "").strip()

    if event_city in _BI_CITY_MAP:
        return _BI_CITY_MAP[event_city]

    if event_city in _VALID_CITIES:
        return [event_city]

    return ["台北", "桃園"]


def _historical_departure_city(artist_name: str) -> str | None:
    try:
        from app.models.event_page import EventPage
        pages = (
            EventPage.query
            .filter(
                EventPage.deleted_at.is_(None),
                EventPage.departure_city.isnot(None),
                EventPage.artist_name.ilike(f"%{artist_name}%"),
            )
            .all()
        )
        cities = [p.departure_city for p in pages if p.departure_city]
        if cities:
            return Counter(cities).most_common(1)[0][0]
    except Exception:
        pass
    return None
