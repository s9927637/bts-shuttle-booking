"""
recommendation_engine — 競爭分數 + 最終推薦決策引擎。

competition_score（0–100）— Rule-Based（預留未來競品資料）：
  高雄大型演唱會（S 級 / A 級藝人）→ 85（高需求低競爭）
  台北大型演唱會（S 級藝人）         → 70
  台北中型演唱會（A 級藝人）         → 60
  其他城市                           → 55
  不明城市                           → 40

recommendation 決策規則（opportunity_score）：
  >= 70 → STRONGLY_RECOMMENDED
  >= 52 → RECOMMENDED
  >= 35 → OBSERVE
  <  35 → NOT_RECOMMENDED

risk_level 決策規則：
  competition_score >= 75 AND demand_score >= 60 → LOW
  opportunity_score >= 55                        → MEDIUM
  otherwise                                      → HIGH
"""
from __future__ import annotations

_S_TIER = {
    "taylor swift", "ed sheeran", "coldplay", "the weeknd", "bruno mars",
    "bts", "blackpink", "seventeen", "stray kids", "nct",
    "五月天", "周杰倫", "張惠妹", "林俊傑",
}
_A_TIER = {
    "ive", "aespa", "newjeans", "itzy", "got7", "exo",
    "蔡依林", "鄧紫棋", "陳奕迅", "韋禮安",
    "yoasobi", "米津玄師", "official髭男dism",
    "charlie puth", "kyuhyun",
    "藤井風", "あいみょん",
}


def compute_competition_score(hub) -> int:
    """Rule-Based 競爭分數。"""
    artist_lower = (hub.artist_name or "").lower()
    city         = (hub.city or "").strip()

    is_s = any(t in artist_lower for t in _S_TIER)
    is_a = any(t in artist_lower for t in _A_TIER)

    if city == "高雄" and (is_s or is_a):
        return 85
    if city == "台北" and is_s:
        return 70
    if city == "台北" and is_a:
        return 60
    if city in ("台中", "台南", "桃園", "新北"):
        return 55
    if city:
        return 50
    return 40


def compute_opportunity_score(
    demand_score:        int,
    historical_score:    int,
    competition_score:   int,
    profitability_score: int,
) -> int:
    """
    加權平均 opportunity_score。
    權重：需求 35% / 歷史 25% / 競爭 20% / 獲利 20%
    """
    score = (
        demand_score        * 0.35
        + historical_score  * 0.25
        + competition_score * 0.20
        + profitability_score * 0.20
    )
    return min(int(round(score)), 100)


def determine_recommendation(opportunity_score: int) -> str:
    if opportunity_score >= 70:
        return "STRONGLY_RECOMMENDED"
    elif opportunity_score >= 52:
        return "RECOMMENDED"
    elif opportunity_score >= 35:
        return "OBSERVE"
    return "NOT_RECOMMENDED"


def determine_risk(
    opportunity_score:  int,
    competition_score:  int,
    demand_score:       int,
) -> str:
    if competition_score >= 75 and demand_score >= 60:
        return "LOW"
    elif opportunity_score >= 55:
        return "MEDIUM"
    return "HIGH"


def build_notes(hub, demand_score: int, competition_score: int, passengers: int) -> str:
    """產生說明文字。"""
    parts = []
    city   = hub.city or "不明城市"
    artist = hub.artist_name or "?"

    parts.append(f"{artist} 在{city}的演唱會。")

    if demand_score >= 70:
        parts.append("市場需求高，建議積極評估。")
    elif demand_score >= 50:
        parts.append("市場需求中等。")
    else:
        parts.append("市場需求較低，需謹慎評估。")

    if competition_score >= 75:
        parts.append("競爭態勢有利（高需求低競爭市場）。")

    parts.append(f"預估可承載 {passengers} 名乘客。")

    return " ".join(parts)
