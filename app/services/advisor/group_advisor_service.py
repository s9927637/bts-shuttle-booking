"""
group_advisor_service — AI 開團顧問主控服務。

對外介面：
  advise(hub, bi)       → AiGroupAdvice（未 commit）
  recalculate_all()     → {"created": N, "updated": N, "total": N}
  recalculate_for(hub_id) → AiGroupAdvice
  get_advisor_stats()   → dashboard 統計 dict

呼叫鏈：
  pricing_advisor  → recommended_price, recommended_deposit
  city_advisor     → recommended_departure_city
  risk_advisor     → risk_level, confidence_score
"""
from __future__ import annotations

import math
from datetime import datetime


_VEHICLE_CAPACITY = 8   # 與 profit_engine 一致


def advise(hub, bi) -> "AiGroupAdvice":
    """
    計算單筆 ConcertDataHub 的開團建議，回傳 AiGroupAdvice（未寫入 DB）。
    """
    from app.models.ai_group_advice import AiGroupAdvice
    from app.services.advisor.pricing_advisor import recommend_price, recommend_deposit
    from app.services.advisor.city_advisor import recommend_departure_city
    from app.services.advisor.risk_advisor import assess_risk, compute_confidence_score

    risk_level       = assess_risk(hub, bi)
    confidence_score = compute_confidence_score(hub, bi)
    price            = recommend_price(hub, bi)
    deposit          = recommend_deposit(risk_level)
    departure_city   = recommend_departure_city(hub, bi)

    pax = bi.estimated_passengers if bi else 8
    vehicles = max(math.ceil(pax / _VEHICLE_CAPACITY), 1)

    summary = _build_summary(
        hub, bi, price, deposit, departure_city, pax, vehicles, risk_level, confidence_score
    )

    return AiGroupAdvice(
        concert_hub_id              = hub.id,
        business_insight_id         = bi.id if bi else None,
        recommended_price           = price,
        recommended_deposit         = deposit,
        recommended_departure_city  = departure_city,
        recommended_vehicle_count   = vehicles,
        recommended_passenger_count = pax,
        risk_level                  = risk_level,
        confidence_score            = confidence_score,
        summary                     = summary,
        created_at                  = datetime.utcnow(),
        updated_at                  = datetime.utcnow(),
    )


def recalculate_all() -> dict:
    """對所有 active ConcertDataHub 重新產生顧問建議。"""
    from app import db
    from app.models.concert_data_hub import ConcertDataHub
    from app.models.business_insight import BusinessInsight
    from app.models.ai_group_advice import AiGroupAdvice

    hubs = ConcertDataHub.query.filter_by(status="active").all()

    bi_map: dict[int, BusinessInsight] = {
        bi.concert_hub_id: bi
        for bi in BusinessInsight.query.all()
    }
    existing: dict[int, AiGroupAdvice] = {
        a.concert_hub_id: a
        for a in AiGroupAdvice.query.all()
    }

    created = updated = 0

    for hub in hubs:
        bi      = bi_map.get(hub.id)
        new_adv = advise(hub, bi)

        if hub.id in existing:
            adv = existing[hub.id]
            for field in (
                "business_insight_id",
                "recommended_price", "recommended_deposit",
                "recommended_departure_city",
                "recommended_vehicle_count", "recommended_passenger_count",
                "risk_level", "confidence_score", "summary",
            ):
                setattr(adv, field, getattr(new_adv, field))
            adv.updated_at = datetime.utcnow()
            updated += 1
        else:
            db.session.add(new_adv)
            created += 1

    db.session.commit()
    return {"created": created, "updated": updated, "total": created + updated}


def recalculate_for(hub_id: int) -> "AiGroupAdvice":
    from app import db
    from app.models.concert_data_hub import ConcertDataHub
    from app.models.business_insight import BusinessInsight
    from app.models.ai_group_advice import AiGroupAdvice

    hub = ConcertDataHub.query.get(hub_id)
    if not hub:
        raise ValueError(f"ConcertDataHub #{hub_id} 不存在")

    bi  = BusinessInsight.query.filter_by(concert_hub_id=hub_id).first()
    existing = AiGroupAdvice.query.filter_by(concert_hub_id=hub_id).first()
    new_adv  = advise(hub, bi)

    if existing:
        for field in (
            "business_insight_id",
            "recommended_price", "recommended_deposit",
            "recommended_departure_city",
            "recommended_vehicle_count", "recommended_passenger_count",
            "risk_level", "confidence_score", "summary",
        ):
            setattr(existing, field, getattr(new_adv, field))
        existing.updated_at = datetime.utcnow()
        db.session.commit()
        return existing
    else:
        db.session.add(new_adv)
        db.session.commit()
        return new_adv


def get_advisor_stats() -> dict:
    """Dashboard 統計。"""
    from app.models.ai_group_advice import AiGroupAdvice

    total    = AiGroupAdvice.query.count()
    low_risk = AiGroupAdvice.query.filter_by(risk_level="LOW").count()
    high_risk = AiGroupAdvice.query.filter_by(risk_level="HIGH").count()
    top_confidence = (
        AiGroupAdvice.query
        .order_by(AiGroupAdvice.confidence_score.desc())
        .first()
    )

    return {
        "total":          total,
        "low_risk":       low_risk,
        "high_risk":      high_risk,
        "top_confidence": top_confidence.confidence_score if top_confidence else 0,
    }


# ── 內部工具 ──────────────────────────────────────────────────────────────────

def _build_summary(hub, bi, price, deposit, departure_city,
                   pax, vehicles, risk_level, confidence_score) -> str:
    artist = hub.artist_name or "—"
    city   = hub.city or "待確認"
    date_str = hub.event_date.strftime("%Y/%m/%d") if hub.event_date else "待確認"

    risk_map = {"LOW": "低", "MEDIUM": "中", "HIGH": "高"}
    risk_zh  = risk_map.get(risk_level, "中")

    opp = bi.opportunity_score if bi else 0
    rec = bi.recommendation if bi else "OBSERVE"
    rec_map = {
        "STRONGLY_RECOMMENDED": "強烈推薦",
        "RECOMMENDED":          "推薦",
        "OBSERVE":              "觀望",
        "NOT_RECOMMENDED":      "不推薦",
    }
    rec_zh = rec_map.get(rec, "觀望")

    return (
        f"【{artist}】{city} {date_str}。"
        f"商機評級：{rec_zh}（分數 {opp}）。"
        f"建議票價 NT${price:,}，訂金 NT${deposit:,}。"
        f"出發城市：{departure_city}；預估 {pax} 名乘客、{vehicles} 輛車。"
        f"風險：{risk_zh}，信心分數：{confidence_score}。"
    )
