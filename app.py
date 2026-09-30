from datetime import datetime, timezone, timedelta

from flask import Flask, redirect, url_for
from flask_login import LoginManager

from services.email_service import mail
from config import Config
from models import db
from models.user import User


login_manager = LoginManager()


def format_ist(value):
    """
    Convert a UTC datetime from the database
    into Indian Standard Time (Asia/Kolkata).
    """
    if not value:
        return "-"

    # IST is a fixed UTC+05:30 offset and does not observe daylight saving time.
    ist_time = value.replace(tzinfo=timezone.utc).astimezone(
        timezone(timedelta(hours=5, minutes=30))
    )

    return ist_time.strftime("%d-%m-%Y %H:%M")


def create_app():

    app = Flask(__name__)

    # Register IST filter for Jinja templates
    app.jinja_env.filters["ist"] = format_ist

    # --------------------------------
    # Configuration
    # --------------------------------
    app.config.from_object(Config)

    # --------------------------------
    # Database
    # --------------------------------
    db.init_app(app)

    # --------------------------------
    # Login Manager
    # --------------------------------
    login_manager.init_app(app)

    mail.init_app(app)

    login_manager.login_view = "auth.login"

    # --------------------------------
    # User Loader
    # --------------------------------
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # --------------------------------
    # Register Blueprints
    # --------------------------------
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.email import email_bp
    from models.campaign import Campaign, CampaignRecipient, Suppression

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(email_bp)

    # --------------------------------
    # Home Route
    # --------------------------------
    @app.route("/")
    def home():
        return redirect(url_for("dashboard.dashboard"))

    # --------------------------------
    # Create Database Tables
    # --------------------------------
    with app.app_context():
        db.create_all()
        # Load model classes before create_all without changing existing email_logs.
        _ = (Campaign, CampaignRecipient, Suppression)

    return app


# --------------------------------
# Create Flask Application
# --------------------------------

app = create_app()


# --------------------------------
# Run Application
# --------------------------------

if __name__ == "__main__":
    app.run(debug=True)
