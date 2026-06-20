"""
爬蟲管理中心 Blueprint

後台管理頁：  GET  /admin/crawlers
API：         POST /api/crawlers/run
              GET  /api/crawlers/jobs
              GET  /api/crawlers/logs/<job_id>
"""
from datetime import datetime

from flask import Blueprint, jsonify, render_template, request, session

from app import db
from app.models.crawl_job import CrawlJob
from app.models.crawl_log import CrawlLog
from app.services.crawlers import REGISTRY
from app.services.crawlers.crawler_manager import (
    run_kktix, run_tixcraft, run_all, run_playwright_test,
)

crawler_bp = Blueprint("crawler", __name__)


def _require_admin():
    if not session.get("admin_id"):
        return None, (jsonify({"error": "未登入"}), 401)
    return True, None


def _require_admin_page():
    from flask import redirect
    if not session.get("admin_id"):
        return redirect("/admin/login")
    return None


# ── 後台管理頁 ─────────────────────────────────────────────────────────────────

@crawler_bp.route("/admin/crawlers")
def crawler_index():
    guard = _require_admin_page()
    if guard:
        return guard

    jobs = CrawlJob.query.order_by(CrawlJob.created_at.desc()).limit(50).all()
    sources = list(REGISTRY.keys())
    return render_template("admin/crawlers/index.html", jobs=jobs, sources=sources)


# ── API: 手動執行爬蟲 ──────────────────────────────────────────────────────────

@crawler_bp.route("/api/crawlers/run", methods=["POST"])
def api_crawler_run():
    ok, err = _require_admin()
    if not ok:
        return err

    data = request.get_json(silent=True) or {}
    source = data.get("source", "mock")

    if source not in REGISTRY:
        return jsonify({"error": f"未知來源：{source}，可用：{list(REGISTRY.keys())}"}), 400

    # 建立 job
    job = CrawlJob(
        source_name=source,
        status="running",
        started_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
    )
    db.session.add(job)
    db.session.commit()

    try:
        crawler_cls = REGISTRY[source]
        crawler = crawler_cls(job_id=job.id)
        created, updated, skipped, errors = crawler.run()

        job.status        = "success" if errors == 0 else "error"
        job.finished_at   = datetime.utcnow()
        job.created_count = created
        job.updated_count = updated
        job.skipped_count = skipped
        job.error_count   = errors
        if errors == 0:
            job.last_success_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            "job_id":  job.id,
            "status":  job.status,
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "errors":  errors,
        })

    except Exception as exc:
        job.status      = "error"
        job.finished_at = datetime.utcnow()
        job.error_count = 1
        db.session.commit()
        return jsonify({"job_id": job.id, "status": "error", "error": str(exc)}), 500


# ── API: 取得 job 列表 ─────────────────────────────────────────────────────────

@crawler_bp.route("/api/crawlers/jobs")
def api_crawler_jobs():
    ok, err = _require_admin()
    if not ok:
        return err

    jobs = CrawlJob.query.order_by(CrawlJob.created_at.desc()).limit(20).all()
    return jsonify([
        {
            "id":            j.id,
            "source_name":   j.source_name,
            "status":        j.status,
            "created_count": j.created_count,
            "updated_count": j.updated_count,
            "skipped_count": j.skipped_count,
            "error_count":   j.error_count,
            "started_at":    j.started_at.isoformat() if j.started_at else None,
            "finished_at":   j.finished_at.isoformat() if j.finished_at else None,
            "duration_s":    j.duration_seconds,
            "created_at":    j.created_at.isoformat() if j.created_at else None,
        }
        for j in jobs
    ])


# ── API: 取得特定 job 的 logs ──────────────────────────────────────────────────

@crawler_bp.route("/api/crawlers/logs/<int:job_id>")
def api_crawler_logs(job_id):
    ok, err = _require_admin()
    if not ok:
        return err

    logs = CrawlLog.query.filter_by(job_id=job_id).order_by(CrawlLog.created_at).all()
    return jsonify([
        {
            "id":          l.id,
            "level":       l.level,
            "message":     l.message,
            "created_at":  l.created_at.isoformat() if l.created_at else None,
        }
        for l in logs
    ])


# ── API: Playwright 測試（example.com pipeline 驗證）────────────────────────

@crawler_bp.route("/api/crawlers/test", methods=["POST"])
def api_crawler_test():
    ok, err = _require_admin()
    if not ok:
        return err
    try:
        result = run_playwright_test()
        return jsonify(result), 200
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500


# ── API: 執行 KKTIX 爬蟲 ─────────────────────────────────────────────────────

@crawler_bp.route("/api/crawlers/kktix", methods=["POST"])
def api_crawler_kktix():
    ok, err = _require_admin()
    if not ok:
        return err
    try:
        result = run_kktix()
        return jsonify(result), 200
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500


# ── API: 執行 TixCraft 爬蟲 ──────────────────────────────────────────────────

@crawler_bp.route("/api/crawlers/tixcraft", methods=["POST"])
def api_crawler_tixcraft():
    ok, err = _require_admin()
    if not ok:
        return err
    try:
        result = run_tixcraft()
        return jsonify(result), 200
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500


# ── API: 全部執行 ─────────────────────────────────────────────────────────────

@crawler_bp.route("/api/crawlers/run-all", methods=["POST"])
def api_crawler_run_all():
    ok, err = _require_admin()
    if not ok:
        return err
    try:
        results = run_all()
        total_created = sum(r.get("created", 0) for r in results)
        total_updated = sum(r.get("updated", 0) for r in results)
        return jsonify({
            "results":       results,
            "total_created": total_created,
            "total_updated": total_updated,
        }), 200
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500
