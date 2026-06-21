"""
demand_engine — 需求分數 + 歷史分數計算引擎。

demand_score（0–100）規則：
  城市吸引力
    台北        +35
    高雄        +28
    台中        +22
    新北/桃園   +18
    其他        +12
  藝人等級（預設規則）
    S 級（國際頂流）+40
    A 級（知名藝人）+30
    B 級（新興/本土）+20
    未知           +10
  有明確日期   +10
  有場館資訊   +15  ← 上限調整至 100

historical_score（0–100）規則：
  有過去 EventMetrics 資料（同藝人 / 同城市）
    booking_count > 50  → +50（人氣高）
    booking_count 20–50 → +35
    booking_count < 20  → +20
  conversion_rate（付款轉換率）
    > 80% → +30
    50–80% → +20
    < 50%  → +10
  無歷史資料      → baseline 30
"""
from __future__ import annotations

import math

_CITY_SCORE: dict[str, int] = {
    "台北": 35, "臺北": 35,
    "高雄": 28, "台中": 22,
    "新北": 18, "桃園": 18,
    "台南": 16, "嘉義": 14,
    "宜蘭": 12, "花蓮": 12, "台東": 12,
    "新竹": 14,
    "東京": 20, "大阪": 18,
    "首爾": 20,
    "線上": 8,
}

# S 級：國際頂流（場館 3 萬人+）
_S_TIER = {
    "taylor swift", "ed sheeran", "coldplay", "the weeknd", "bruno mars",
    "bts", "blackpink", "seventeen", "stray kids", "nct",
    "五月天", "周杰倫", "張惠妹", "林俊傑",
}
# A 級：知名藝人（場館 1 萬人+）
_A_TIER = {
    "ive", "aespa", "newjeans", "itzy", "got7", "exo",
    "蔡依林", "鄧紫棋", "陳奕迅", "韋禮安",
    "yoasobi", "米津玄師", "official髭男dism",
    "charlie puth", "kyuhyun",
    "藤井風", "あいみょん",
}


def compute_demand_score(hub) -> int:
    """計算 demand_score。"""
    score = 0

    # 城市分數
    city = (hub.city or "").strip()
    score += _CITY_SCORE.get(city, 12)

    # 藝人等級
    artist_lower = (hub.artist_name or "").lower()
    if any(t in artist_lower for t in _S_TIER):
        score += 40
    elif any(t in artist_lower for t in _A_TIER):
        score += 30
    else:
        score += 10

    # 有日期 +10
    if hub.event_date:
        score += 10

    # 有場館 +15
    if hub.venue and hub.venue not in ("待確認", "TBD", ""):
        score += 15

    return min(score, 100)


def compute_historical_score(hub) -> int:
    """
    依據過去相似 EventPage 的 EventMetrics 計算歷史分數。
    相似定義：同藝人名稱（模糊匹配）或同城市。
    """
    from app.models.event_page import EventPage
    from app.models.event_metrics import EventMetrics

    # 找同藝人 EventPage
    artist = (hub.artist_name or "").strip()
    city   = (hub.city or "").strip()

    pages = EventPage.query.filter(
        EventPage.deleted_at.is_(None),
        EventPage.artist_name.ilike(f"%{artist}%"),
    ).all()

    # 若同藝人無資料，改找同城市
    if not pages and city and city not in ("待確認", ""):
        pages = EventPage.query.filter(
            EventPage.deleted_at.is_(None),
            EventPage.departure_city.ilike(f"%{city}%"),
        ).limit(5).all()

    if not pages:
        return 30  # baseline

    # 彙整所有 metrics
    total_booking  = 0
    total_paid     = 0
    metrics_count  = 0

    for ep in pages:
        m = EventMetrics.query.filter_by(event_page_id=ep.id).first()
        if not m:
            continue
        total_booking += m.booking_count
        total_paid    += m.paid_count
        metrics_count += 1

    if metrics_count == 0:
        return 30

    avg_booking = total_booking / metrics_count
    conv_rate   = (total_paid / total_booking * 100) if total_booking else 0

    score = 0

    # 預訂量分數
    if avg_booking > 50:
        score += 50
    elif avg_booking >= 20:
        score += 35
    else:
        score += 20

    # 轉換率分數
    if conv_rate > 80:
        score += 30
    elif conv_rate >= 50:
        score += 20
    else:
        score += 10

    return min(score, 100)


def estimate_passengers(demand_score: int, city: str) -> int:
    """依需求分數和城市估算乘客人數。"""
    # 基礎客量依城市
    _BASE: dict[str, int] = {
        "台北": 24, "高雄": 20, "台中": 16,
        "新北": 14, "桃園": 12,
    }
    base = _BASE.get(city, 10)

    # 依需求分數乘上係數
    multiplier = 1.0
    if demand_score >= 70:
        multiplier = 2.5
    elif demand_score >= 50:
        multiplier = 1.8
    elif demand_score >= 30:
        multiplier = 1.3

    return max(int(base * multiplier), 4)
