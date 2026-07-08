from datetime import timedelta
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv
import os

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()

from app.models.admin import Admin
from app.models.order import Order
from app.models.payment import Payment
from app.models.vehicle import Vehicle
from app.models.driver import Driver
from app.models.announcement import Announcement
from app.models.notification import Notification
from app.models.receipt import Receipt
from app.models.audit_log import AuditLog
from app.models.coupon import Coupon
from app.models.concert import Concert, ConcertMetrics, ConcertOpportunity, EventGroup
from app.models.event_page import EventPage
from app.models.event_metrics import EventMetrics
from app.models.crawl_job import CrawlJob
from app.models.crawl_log import CrawlLog
from app.models.event_template import EventTemplate
from app.models.group_creation_job import GroupCreationJob
from app.models.concert_data_hub import ConcertDataHub
from app.models.business_insight import BusinessInsight
from app.models.ai_group_advice import AiGroupAdvice
from app.models.crawler_source_status import CrawlerSourceStatus
from app.models.system_health_check import SystemHealthCheck
from app.models.order_event import OrderEvent
from app.models.dispatch_event import DispatchEvent, DispatchEventOrder
from app.models.passenger_profile import PassengerProfile, PassengerTag
from app.models.crawler_audit_log import CrawlerAuditLog
from app.models.event_booking import EventBookingDate, EventPickupLocation, EventPriceRule, EventFormConfig
from app.models.event_hotspot import EventHotspot

def create_app():
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    secret = os.getenv("SECRET_KEY")
    if not secret:
        raise RuntimeError("SECRET_KEY environment variable is not set")
    app.config["SECRET_KEY"] = secret
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)
    app.config["WTF_CSRF_TIME_LIMIT"] = None  # token 不過期（配合長表單操作）

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    from app.routes.passenger import passenger_bp
    from app.routes.admin import admin_bp
    from app.routes.auth import auth_bp
    from app.routes.dispatch import dispatch_bp
    from app.routes.driver import driver_bp
    from app.routes.line_webhook import line_webhook_bp
    from app.routes.concert import concert_bp
    from app.routes.event_page import event_page_bp
    from app.routes.crawler import crawler_bp
    from app.routes.group_creation import group_bp
    from app.routes.concert_hub import hub_bp
    from app.routes.business_intelligence import bi_bp
    from app.routes.group_advisor import advisor_bp
    from app.routes.crawler_coverage import coverage_bp
    from app.routes.system_health import health_bp
    from app.routes.event_dispatch import event_dispatch_bp
    from app.routes.passenger_center import passenger_center_bp

    app.register_blueprint(passenger_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dispatch_bp)
    app.register_blueprint(driver_bp)
    app.register_blueprint(line_webhook_bp)
    app.register_blueprint(concert_bp)
    app.register_blueprint(event_page_bp)
    app.register_blueprint(crawler_bp)
    app.register_blueprint(group_bp)
    app.register_blueprint(hub_bp)
    app.register_blueprint(bi_bp)
    app.register_blueprint(advisor_bp)
    app.register_blueprint(coverage_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(event_dispatch_bp)
    app.register_blueprint(passenger_center_bp)

    # Register Jinja filters
    from app.utils.css_scope import scope_css as _scope_css
    @app.template_filter('scope_css')
    def _scope_css_filter(raw_css, slug):
        return _scope_css(raw_css, slug)

    # Current Event Context：/events/<slug>/* 底下的路由（見 event_page_bp.before_request）
    # 統一在 g.current_event 解析一次，這裡自動注入到所有 template，
    # 不需要每個 render_template() 手動傳入。與各路由既有的 ep=/event_page= 參數並存，
    # 不影響既有 template 的 Logo/Navbar/Booking/Orders/Announcement 顯示邏輯。
    from flask import g as _g
    @app.context_processor
    def _inject_current_event():
        return dict(current_event=getattr(_g, 'current_event', None))

    import logging
    from flask import render_template as _rt

    logging.basicConfig(level=logging.ERROR)

    @app.errorhandler(500)
    def internal_error(exc):
        app.logger.error("未捕捉的系統錯誤: %s", exc, exc_info=True)
        db.session.rollback()
        return _rt("errors/500.html"), 500

    @app.errorhandler(404)
    def not_found(exc):
        return _rt("errors/404.html"), 404

    return app
