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

    app.register_blueprint(passenger_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dispatch_bp)
    app.register_blueprint(driver_bp)

    return app
