"""
AI 開團顧問 Blueprint

後台頁面：
  GET  /admin/group-advisor               顧問建議頁

API：
  GET  /api/group-advisor                 全部建議列表
  GET  /api/group-advisor/<id>            單筆建議
  POST /api/group-advisor/recalculate     重新計算所有建議
"""
from flask import Blueprint, jsonify, render_template, session, redirect, request

from app.models.ai_group_advice import AiGroupAdvice
from app.models.concert_data_hub import ConcertDataHub

advisor_bp = Blueprint("advisor", __name__)


def _require_admin():
    if not session.get("admin_id"):
        return None, (jsonify({"error": "未登入"}), 401)
    return True, None


def _require_admin_page():
    if not session.get("admin_id"):
        return redirect("/admin/login")
    return None


# ── 後台頁面 ─────────────────────────────────────────────────────────────────

@advisor_bp.route("/admin/group-advisor")
def advisor_index():
    guard = _require_admin_page()
    if guard:
        return guard

    advices = (
        AiGroupAdvice.query
        .join(ConcertDataHub, AiGroupAdvice.concert_hub_id == ConcertDataHub.id)
        .filter(ConcertDataHub.status == "active")
        .order_by(AiGroupAdvice.confidence_score.desc())
        .all()
    )

    total      = len(advices)
    low_risk   = sum(1 for a in advices if a.risk_level == "LOW")
    high_risk  = sum(1 for a in advices if a.risk_level == "HIGH")
    high_conf  = sum(1 for a in advices if a.confidence_score >= 70)

    from app.models.event_template import EventTemplate
    default_template = EventTemplate.query.filter_by(status="啟用").first()

    return render_template(
        "admin/group_advisor/index.html",
        advices=advices,
        total=total,
        low_risk=low_risk,
        high_risk=high_risk,
        high_conf=high_conf,
        default_template=default_template,
    )


# ── API ───────────────────────────────────────────────────────────────────────

@advisor_bp.route("/api/group-advisor")
def api_advisor_list():
    ok, err = _require_admin()
    if not ok:
        return err

    page     = request.args.get("page",     1,  type=int)
    per_page = request.args.get("per_page", 50, type=int)
    risk     = request.args.get("risk")

    q = (
        AiGroupAdvice.query
        .join(ConcertDataHub, AiGroupAdvice.concert_hub_id == ConcertDataHub.id)
        .filter(ConcertDataHub.status == "active")
    )
    if risk:
        q = q.filter(AiGroupAdvice.risk_level == risk.upper())

    total = q.count()
    items = (
        q.order_by(AiGroupAdvice.confidence_score.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return jsonify({
        "total": total,
        "page":  page,
        "items": [_adv_to_dict(a) for a in items],
    })


@advisor_bp.route("/api/group-advisor/<int:adv_id>")
def api_advisor_detail(adv_id: int):
    ok, err = _require_admin()
    if not ok:
        return err

    adv = AiGroupAdvice.query.get_or_404(adv_id)
    return jsonify(_adv_to_dict(adv))


@advisor_bp.route("/api/group-advisor/recalculate", methods=["POST"])
def api_advisor_recalculate():
    ok, err = _require_admin()
    if not ok:
        return err

    try:
        from app.services.advisor.group_advisor_service import recalculate_all
        result = recalculate_all()
        return jsonify({"status": "ok", **result}), 200
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500


# ── 工具 ──────────────────────────────────────────────────────────────────────

def _adv_to_dict(adv: AiGroupAdvice) -> dict:
    hub = adv.hub
    bi  = adv.insight
    return {
        "id":                          adv.id,
        "concert_hub_id":              adv.concert_hub_id,
        "business_insight_id":         adv.business_insight_id,
        "artist_name":                 hub.artist_name  if hub else None,
        "concert_name":                hub.concert_name if hub else None,
        "event_date":                  str(hub.event_date) if hub and hub.event_date else None,
        "city":                        hub.city         if hub else None,
        "recommended_price":           adv.recommended_price,
        "recommended_deposit":         adv.recommended_deposit,
        "recommended_departure_city":  adv.recommended_departure_city,
        "recommended_vehicle_count":   adv.recommended_vehicle_count,
        "recommended_passenger_count": adv.recommended_passenger_count,
        "risk_level":                  adv.risk_level,
        "risk_label":                  adv.risk_label,
        "confidence_score":            adv.confidence_score,
        "confidence_label":            adv.confidence_label,
        "summary":                     adv.summary,
        "opportunity_score":           bi.opportunity_score if bi else None,
        "recommendation":              bi.recommendation   if bi else None,
        "updated_at":                  adv.updated_at.isoformat() if adv.updated_at else None,
    }
