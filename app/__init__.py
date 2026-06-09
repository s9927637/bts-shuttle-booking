from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv
import os

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()

from app.models.admin import Admin
from app.models.order import Order
from app.models.payment import Payment
from app.models.vehicle import Vehicle
from app.models.driver import Driver
from app.models.announcement import Announcement
from app.models.notification import Notification

def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    migrate.init_app(app, db)

    from app.routes.passenger import passenger_bp
    from app.routes.admin import admin_bp
    from app.routes.auth import auth_bp
    from app.routes.dispatch import dispatch_bp

    app.register_blueprint(passenger_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dispatch_bp)

    return app
