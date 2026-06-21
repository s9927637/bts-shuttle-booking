"""
系統健康度中心 Blueprint

Routes:
  GET  /admin/system-health          → index（列表頁）
  GET  /api/system-health            → JSON 讀取現有結果
  POST /api/system-health/run        → 執行全部檢查並回傳結果
"""
from flask import Blueprint, render_template, jsonify, session, redirect, url_for

health_bp = Blueprint("health", __name__)


def _require_admin():
    return session.get("admin_id")


@health_bp.route("/admin/system-health")
def health_index():
    if not _require_admin():
        return redirect(url_for("admin.login"))

    from app.services.system_health.health_check_service import get_all_results, get_summary
    results = get_all_results()
    summary = get_summary()
    return render_template("admin/system_health/index.html",
                           results=results, summary=summary)


@health_bp.route("/api/system-health")
def api_health_get():
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 401
    from app.services.system_health.health_check_service import get_all_results, get_summary
    results = get_all_results()
    summary = get_summary()
    return jsonify({"results": results, "summary": summary})


@health_bp.route("/api/system-health/run", methods=["POST"])
def api_health_run():
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 401
    from app.services.system_health.health_check_service import run_all, get_summary
    results = run_all()
    summary = get_summary()
    return jsonify({"ok": True, "results": results, "summary": summary})
