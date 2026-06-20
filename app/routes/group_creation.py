"""
自動開團中心 Blueprint

後台管理：
  GET  /admin/recommended-groups     推薦開團列表
  GET  /admin/event-templates        價格模板管理
  POST /admin/event-templates        新增模板
  POST /admin/event-templates/<id>/delete  刪除模板

API（JSON）：
  POST /api/groups/create            一鍵開團
  GET  /api/groups/jobs              Job 列表
  GET  /api/groups/recommended       推薦列表
"""
from datetime import datetime

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from app import db
from app.models.event_template import EventTemplate
from app.models.group_creation_job import GroupCreationJob

group_bp = Blueprint("group", __name__)


def _require_admin():
    if not session.get("admin_id"):
        return redirect("/admin/login")
    return None


# ── 後台：推薦開團頁 ────────────────────────────────────────────────────────

@group_bp.route("/admin/recommended-groups")
def recommended_groups():
    guard = _require_admin()
    if guard:
        return guard

    from app.services.group_creation_service import get_recommended_concerts
    recommended = get_recommended_concerts()
    templates   = EventTemplate.query.filter_by(status="啟用").order_by(EventTemplate.id).all()
    recent_jobs = (
        GroupCreationJob.query
        .order_by(GroupCreationJob.created_at.desc())
        .limit(20)
        .all()
    )
    return render_template(
        "admin/recommended_groups.html",
        recommended=recommended,
        templates=templates,
        recent_jobs=recent_jobs,
    )


# ── 後台：價格模板管理 ──────────────────────────────────────────────────────

@group_bp.route("/admin/event-templates", methods=["GET", "POST"])
def template_list():
    guard = _require_admin()
    if guard:
        return guard

    if request.method == "POST":
        name   = request.form.get("template_name", "").strip()
        city   = request.form.get("departure_city", "").strip()
        price  = int(request.form.get("price", 2000) or 2000)
        dep    = int(request.form.get("deposit", 300) or 300)
        if not name:
            flash("模板名稱為必填。", "error")
        else:
            t = EventTemplate(
                template_name  = name,
                departure_city = city or None,
                price          = price,
                deposit        = dep,
                status         = "啟用",
                created_at     = datetime.utcnow(),
            )
            db.session.add(t)
            db.session.commit()
            flash(f"已建立模板「{name}」。", "success")
        return redirect(url_for("group.template_list"))

    templates = EventTemplate.query.order_by(EventTemplate.id).all()
    return render_template("admin/event_templates.html", templates=templates)


@group_bp.route("/admin/event-templates/<int:t_id>/delete", methods=["POST"])
def template_delete(t_id):
    guard = _require_admin()
    if guard:
        return guard

    t = EventTemplate.query.get_or_404(t_id)
    db.session.delete(t)
    db.session.commit()
    flash(f"已刪除模板「{t.template_name}」。", "success")
    return redirect(url_for("group.template_list"))


# ── API：一鍵開團 POST /api/groups/create ───────────────────────────────────

@group_bp.route("/api/groups/create", methods=["POST"])
def api_create_group():
    if not session.get("admin_id"):
        return jsonify({"error": "未登入"}), 401

    data           = request.get_json(silent=True) or {}
    concert_id     = data.get("concert_id") or request.form.get("concert_id")
    template_id    = data.get("template_id") or request.form.get("template_id")
    opportunity_id = data.get("opportunity_id") or request.form.get("opportunity_id")

    if not concert_id:
        return jsonify({"error": "concert_id 為必填"}), 400

    from app.services.group_creation_service import create_group
    result = create_group(
        concert_id     = int(concert_id),
        template_id    = int(template_id) if template_id else None,
        opportunity_id = int(opportunity_id) if opportunity_id else None,
    )

    if result.success:
        ep = result.event_page
        return jsonify({
            "status":        "success",
            "job_id":        result.job.id,
            "event_page_id": ep.id,
            "slug":          ep.slug,
            "title":         ep.title,
            "url":           f"/admin/events/{ep.id}",
        }), 201

    if result.job.status == "duplicate":
        ep = result.event_page
        return jsonify({
            "status":        "duplicate",
            "message":       result.error,
            "job_id":        result.job.id,
            "event_page_id": ep.id if ep else None,
            "url":           f"/admin/events/{ep.id}" if ep else None,
        }), 409

    return jsonify({
        "status":  "error",
        "message": result.error,
        "job_id":  result.job.id,
    }), 500


# ── API：Job 列表 GET /api/groups/jobs ──────────────────────────────────────

@group_bp.route("/api/groups/jobs")
def api_jobs():
    if not session.get("admin_id"):
        return jsonify({"error": "未登入"}), 401

    limit  = min(int(request.args.get("limit", 50)), 200)
    jobs   = GroupCreationJob.query.order_by(GroupCreationJob.created_at.desc()).limit(limit).all()
    return jsonify({
        "jobs": [
            {
                "id":             j.id,
                "concert_id":     j.concert_id,
                "event_page_id":  j.event_page_id,
                "template_id":    j.template_id,
                "status":         j.status,
                "error_message":  j.error_message,
                "created_at":     j.created_at.isoformat() if j.created_at else None,
            }
            for j in jobs
        ],
        "total": len(jobs),
    })


# ── API：推薦列表 GET /api/groups/recommended ────────────────────────────────

@group_bp.route("/api/groups/recommended")
def api_recommended():
    if not session.get("admin_id"):
        return jsonify({"error": "未登入"}), 401

    from app.services.group_creation_service import get_recommended_concerts
    recommended = get_recommended_concerts()
    return jsonify({
        "recommended": [
            {
                "concert_id":       r["concert"].id,
                "artist":           r["concert"].artist,
                "concert_name":     r["concert"].name,
                "city":             r["concert"].city,
                "event_date":       r["concert"].concert_date.isoformat() if r["concert"].concert_date else None,
                "opportunity_score": r["metrics"].opportunity_score,
                "est_passengers":   r["metrics"].est_passengers,
                "est_revenue":      r["metrics"].est_revenue,
            }
            for r in recommended
        ],
        "total": len(recommended),
    })
