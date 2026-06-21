"""
Crawler Coverage Diagnostics Blueprint

後台頁面：
  GET  /admin/crawlers/coverage        覆蓋率診斷頁

API：
  GET  /api/crawlers/coverage          覆蓋率 JSON
  POST /api/crawlers/coverage/refresh  刷新所有來源狀態
"""
from flask import Blueprint, jsonify, render_template, session, redirect

from app.models.crawler_source_status import CrawlerSourceStatus

coverage_bp = Blueprint("coverage", __name__)


def _require_admin_page():
    if not session.get("admin_id"):
        return redirect("/admin/login")
    return None


def _require_admin():
    if not session.get("admin_id"):
        return None, (jsonify({"error": "未登入"}), 401)
    return True, None


# ── 後台頁面 ─────────────────────────────────────────────────────────────────

@coverage_bp.route("/admin/crawlers/coverage")
def coverage_index():
    guard = _require_admin_page()
    if guard:
        return guard

    from app.services.crawler_coverage_service import (
        get_coverage_data, get_gap_analysis, get_final_report,
    )

    coverage  = get_coverage_data()
    gap       = get_gap_analysis()
    report    = get_final_report()

    return render_template(
        "admin/crawlers/coverage.html",
        coverage=coverage,
        gap=gap,
        report=report,
    )


# ── API ───────────────────────────────────────────────────────────────────────

@coverage_bp.route("/api/crawlers/coverage")
def api_coverage():
    ok, err = _require_admin()
    if not ok:
        return err

    from app.services.crawler_coverage_service import get_coverage_data, get_gap_analysis
    return jsonify({
        "coverage": get_coverage_data(),
        "gap":      get_gap_analysis(),
    })


@coverage_bp.route("/api/crawlers/coverage/refresh", methods=["POST"])
def api_coverage_refresh():
    ok, err = _require_admin()
    if not ok:
        return err

    try:
        from app.services.crawler_coverage_service import refresh
        rows = refresh()
        return jsonify({"status": "ok", "total": len(rows)}), 200
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500
