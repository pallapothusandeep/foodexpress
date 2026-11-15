import os

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app(test_config=None):
    app = Flask(__name__)

    # All settings come from environment variables (12-factor style).
    # Locally it falls back to SQLite; on AWS, DATABASE_URL points to RDS MySQL.
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///foodapp.db"),
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
        S3_BUCKET=os.environ.get("S3_BUCKET", ""),
        AWS_REGION=os.environ.get("AWS_REGION", "ap-south-1"),
        ADMIN_EMAIL=os.environ.get("ADMIN_EMAIL", "admin@foodapp.com"),
        ADMIN_PASSWORD=os.environ.get("ADMIN_PASSWORD", "admin123"),
        APP_VERSION=os.environ.get("APP_VERSION", "1.0"),
        MAX_CONTENT_LENGTH=5 * 1024 * 1024,  # 5 MB upload limit
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"

    from . import models
    from .admin import bp as admin_bp
    from .auth import bp as auth_bp
    from .shop import bp as shop_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(shop_bp)
    app.register_blueprint(admin_bp)

    @app.context_processor
    def inject_globals():
        from flask import session
        cart = session.get("cart", {})
        return {"cart_count": sum(cart.values()), "app_version": app.config["APP_VERSION"]}

    with app.app_context():
        db.create_all()
        models.seed(app)

    return app
