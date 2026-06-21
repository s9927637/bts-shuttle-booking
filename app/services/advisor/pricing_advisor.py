"""
pricing_advisor — 票價 / 訂金建議引擎（Rule-Based）。

邏輯來源：
  1. 同藝人 EventPage 歷史均價
  2. 城市距離係數（高雄 > 台南 > 台中 > 桃園/新竹 > 台北/新北）
  3. 需求強度（demand_score）加成

訂金建議（依風險等級）：
  LOW    → NT$300
  MEDIUM → NT$500
  HIGH   → NT$1,000
"""
from __future__ import annotations

_BASE_PRICE = 2_000   # NT$

_CITY_MULTIPLIER: dict[str, float] = {
    "高雄": 1.30,
    "台南": 1.20,
    "台中": 1.10,
    "桃園": 1.05,
    "新竹": 1.05,
    "新北": 1.00,
    "台北": 1.00,
}

_DEPOSIT_BY_RISK = {
    "LOW":    300,
    "MEDIUM": 500,
    "HIGH":   1_000,
}


def recommend_price(hub, bi) -> int:
    """
    建議票價（NT$）。

    hub : ConcertDataHub
    bi  : BusinessInsight（可為 None）
    """
    # 1. 優先取同藝人歷史均價
    avg = _historical_avg_price(hub.artist_name)

    base = avg if avg else _BASE_PRICE

    # 2. 城市距離加成
    city = (hub.city or "台北").strip()
    mult = _CITY_MULTIPLIER.get(city, 1.00)

    # 3. 需求強度加成（demand_score >= 70 → +10%）
    demand_bonus = 1.10 if (bi and bi.demand_score >= 70) else 1.00

    price = int(base * mult * demand_bonus)

    # 四捨五入到最近 100
    price = round(price / 100) * 100
    return max(price, 1_000)


def recommend_deposit(risk_level: str) -> int:
    return _DEPOSIT_BY_RISK.get(risk_level, 500)


# ── 內部工具 ──────────────────────────────────────────────────────────────────

def _historical_avg_price(artist_name: str) -> int | None:
    """查詢同藝人歷史 EventPage 均價，無資料回傳 None。"""
    try:
        from app.models.event_page import EventPage
        pages = (
            EventPage.query
            .filter(
                EventPage.deleted_at.is_(None),
                EventPage.price.isnot(None),
                EventPage.artist_name.ilike(f"%{artist_name}%"),
            )
            .all()
        )
        prices = [p.price for p in pages if p.price and p.price > 0]
        if prices:
            return int(sum(prices) / len(prices))
    except Exception:
        pass
    return None
