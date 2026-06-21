"""
Business Intelligence Blueprint

後台頁面：
  GET  /admin/business-intelligence     商機決策頁

API：
  GET  /api/business-intelligence            全部商機列表
  GET  /api/business-intelligence/<id>       單筆商機
  POST /api/business-intelligence/recalculate 全部重算
"""
from flask import Blueprint, jsonify, render_template, session, redirect, request

from app.models.business_insight import BusinessInsight
from app.models.concert_data_hub import ConcertDataHub

bi_bp = Blueprint("bi", __name__)


def _require_admin():
    if not session.get("admin_id"):
        return None, (jsonify({"error": "未登入"}), 401)
    return True, None


def _require_admin_page():
    if not session.get("admin_id"):
        return redirect("/admin/login")
    return None


# ── 後台頁面 ─────────────────────────────────────────────────────────────────

@bi_bp.route("/admin/business-intelligence")
def bi_index():
    guard = _require_admin_page()
    if guard:
        return guard

    insights = (
        BusinessInsight.query
        .join(ConcertDataHub, BusinessInsight.concert_hub_id == ConcertDataHub.id)
        .filter(ConcertDataHub.status == "active")
        .order_by(BusinessInsight.opportunity_score.desc())
        .all()
    )

    # 統計
    total         = len(insights)
    strong_count  = sum(1 for i in insights if i.recommendation == "STRONGLY_RECOMMENDED")
    rec_count     = sum(1 for i in insights if i.recommendation == "RECOMMENDED")

    # 取第一個啟用模板
    from app.models.event_template import EventTemplate
    default_template = EventTemplate.query.filter_by(status="啟用").first()

    return render_template(
        "admin/business_intelligence/index.html",
        insights=insights,
        total=total,
        strong_count=strong_count,
        rec_count=rec_count,
        default_template=default_template,
    )


# ── API ───────────────────────────────────────────────────────────────────────

@bi_bp.route("/api/business-intelligence")
def api_bi_list():
    ok, err = _require_admin()
    if not ok:
        return err

    page     = request.args.get("page",     1,  type=int)
    per_page = request.args.get("per_page", 50, type=int)
    rec      = request.args.get("recommendation")

    q = (
        BusinessInsight.query
        .join(ConcertDataHub, BusinessInsight.concert_hub_id == ConcertDataHub.id)
        .filter(ConcertDataHub.status == "active")
    )
    if rec:
        q = q.filter(BusinessInsight.recommendation == rec)

    total = q.count()
    items = (
        q.order_by(BusinessInsight.opportunity_score.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return jsonify({
        "total": total,
        "page":  page,
        "items": [_bi_to_dict(i) for i in items],
    })


@bi_bp.route("/api/business-intelligence/<int:bi_id>")
def api_bi_detail(bi_id: int):
    ok, err = _require_admin()
    if not ok:
        return err

    bi = BusinessInsight.query.get_or_404(bi_id)
    return jsonify(_bi_to_dict(bi))


@bi_bp.route("/api/business-intelligence/recalculate", methods=["POST"])
def api_bi_recalculate():
    ok, err = _require_admin()
    if not ok:
        return err

    try:
        from app.services.business_intelligence.insight_engine import recalculate_all
        result = recalculate_all()
        return jsonify({"status": "ok", **result}), 200
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500


# ── 工具 ──────────────────────────────────────────────────────────────────────

def _bi_to_dict(bi: BusinessInsight) -> dict:
    hub = bi.hub
    return {
        "id":                   bi.id,
        "concert_hub_id":       bi.concert_hub_id,
        "artist_name":          hub.artist_name  if hub else None,
        "concert_name":         hub.concert_name if hub else None,
        "event_date":           str(hub.event_date) if hub and hub.event_date else None,
        "city":                 hub.city         if hub else None,
        "source_types":         hub.source_types if hub else None,
        "opportunity_score":    bi.opportunity_score,
        "demand_score":         bi.demand_score,
        "historical_score":     bi.historical_score,
        "competition_score":    bi.competition_score,
        "profitability_score":  bi.profitability_score,
        "estimated_passengers": bi.estimated_passengers,
        "estimated_vehicles":   bi.estimated_vehicles,
        "estimated_revenue":    bi.estimated_revenue,
        "estimated_profit":     bi.estimated_profit,
        "recommendation":       bi.recommendation,
        "recommendation_label": bi.recommendation_label,
        "risk_level":           bi.risk_level,
        "risk_label":           bi.risk_label,
        "notes":                bi.notes,
        "updated_at":           bi.updated_at.isoformat() if bi.updated_at else None,
    }
