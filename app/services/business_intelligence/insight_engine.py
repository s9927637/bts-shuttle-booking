"""
insight_engine — BI 主控引擎。

對外介面：
  calculate(hub)          → BusinessInsight（未 commit）
  recalculate_all()       → {"created": N, "updated": N}
  recalculate_for(hub_id) → BusinessInsight
  get_bi_stats()          → dashboard 統計 dict

呼叫鏈：
  demand_engine  → demand_score, historical_score, estimated_passengers
  profit_engine  → profitability_score, estimated_revenue, estimated_profit, estimated_vehicles
  recommendation_engine → competition_score, opportunity_score, recommendation, risk_level, notes
"""
from __future__ import annotations

from datetime import datetime


def calculate(hub) -> "BusinessInsight":
    """
    計算單筆 ConcertDataHub 的商機分析，回傳 BusinessInsight（未寫入 DB）。
    """
    from app.models.business_insight import BusinessInsight
    from app.services.business_intelligence.demand_engine import (
        compute_demand_score, compute_historical_score, estimate_passengers,
    )
    from app.services.business_intelligence.profit_engine import (
        compute_profit, compute_profitability_score,
    )
    from app.services.business_intelligence.recommendation_engine import (
        compute_competition_score, compute_opportunity_score,
        determine_recommendation, determine_risk, build_notes,
    )

    city = (hub.city or "").strip()
    if city in ("待確認", "TBD"):
        city = ""

    demand_score      = compute_demand_score(hub)
    historical_score  = compute_historical_score(hub)
    competition_score = compute_competition_score(hub)

    passengers        = estimate_passengers(demand_score, city)
    profit_data       = compute_profit(passengers)
    profitability_score = compute_profitability_score(passengers)

    opportunity_score = compute_opportunity_score(
        demand_score, historical_score, competition_score, profitability_score,
    )
    recommendation = determine_recommendation(opportunity_score)
    risk_level     = determine_risk(opportunity_score, competition_score, demand_score)
    notes          = build_notes(hub, demand_score, competition_score, passengers)

    insight = BusinessInsight(
        concert_hub_id       = hub.id,
        opportunity_score    = opportunity_score,
        demand_score         = demand_score,
        historical_score     = historical_score,
        competition_score    = competition_score,
        profitability_score  = profitability_score,
        estimated_passengers = passengers,
        estimated_vehicles   = profit_data["vehicles"],
        estimated_revenue    = profit_data["revenue"],
        estimated_profit     = profit_data["profit"],
        recommendation       = recommendation,
        risk_level           = risk_level,
        notes                = notes,
        created_at           = datetime.utcnow(),
        updated_at           = datetime.utcnow(),
    )
    return insight


def recalculate_all() -> dict:
    """
    對所有 active ConcertDataHub 重新計算商機分析。
    已存在 → UPDATE；不存在 → INSERT。
    """
    from app import db
    from app.models.concert_data_hub import ConcertDataHub
    from app.models.business_insight import BusinessInsight

    hubs = ConcertDataHub.query.filter_by(status="active").all()

    existing: dict[int, BusinessInsight] = {
        bi.concert_hub_id: bi
        for bi in BusinessInsight.query.all()
    }

    created = updated = 0

    for hub in hubs:
        new_bi = calculate(hub)

        if hub.id in existing:
            bi = existing[hub.id]
            bi.opportunity_score    = new_bi.opportunity_score
            bi.demand_score         = new_bi.demand_score
            bi.historical_score     = new_bi.historical_score
            bi.competition_score    = new_bi.competition_score
            bi.profitability_score  = new_bi.profitability_score
            bi.estimated_passengers = new_bi.estimated_passengers
            bi.estimated_vehicles   = new_bi.estimated_vehicles
            bi.estimated_revenue    = new_bi.estimated_revenue
            bi.estimated_profit     = new_bi.estimated_profit
            bi.recommendation       = new_bi.recommendation
            bi.risk_level           = new_bi.risk_level
            bi.notes                = new_bi.notes
            bi.updated_at           = datetime.utcnow()
            updated += 1
        else:
            db.session.add(new_bi)
            created += 1

    db.session.commit()
    return {"created": created, "updated": updated, "total": created + updated}


def recalculate_for(hub_id: int):
    """重新計算單筆 Hub 的商機分析，寫入 DB。"""
    from app import db
    from app.models.concert_data_hub import ConcertDataHub
    from app.models.business_insight import BusinessInsight

    hub = ConcertDataHub.query.get(hub_id)
    if not hub:
        raise ValueError(f"ConcertDataHub #{hub_id} 不存在")

    existing = BusinessInsight.query.filter_by(concert_hub_id=hub_id).first()
    new_bi   = calculate(hub)

    if existing:
        for field in ("opportunity_score", "demand_score", "historical_score",
                      "competition_score", "profitability_score",
                      "estimated_passengers", "estimated_vehicles",
                      "estimated_revenue", "estimated_profit",
                      "recommendation", "risk_level", "notes"):
            setattr(existing, field, getattr(new_bi, field))
        existing.updated_at = datetime.utcnow()
        db.session.commit()
        return existing
    else:
        db.session.add(new_bi)
        db.session.commit()
        return new_bi


def get_bi_stats() -> dict:
    """Dashboard 統計。"""
    from app.models.business_insight import BusinessInsight

    total     = BusinessInsight.query.count()
    strong    = BusinessInsight.query.filter_by(recommendation="STRONGLY_RECOMMENDED").count()
    recommend = BusinessInsight.query.filter_by(recommendation="RECOMMENDED").count()

    return {
        "total":             total,
        "strongly_recommended": strong,
        "recommended":       recommend,
        "actionable":        strong + recommend,
    }
