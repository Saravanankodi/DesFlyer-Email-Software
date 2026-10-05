from datetime import datetime, timezone, timedelta

from flask import Flask, redirect, url_for
from flask_login import LoginManager, current_user

from services.email_service import mail
from config import Config
from models import db
from sqlalchemy import inspect, text
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

    return ist_time.strftime("%d-%m-%Y %I:%M %p")


def format_india_local(value):
    """Format legacy email-log timestamps already stored in India local time."""
    return value.strftime("%d-%m-%Y %I:%M %p") if value else "-"


def create_app():

    app = Flask(__name__)

    # Register IST filter for Jinja templates
    app.jinja_env.filters["ist"] = format_ist
    app.jinja_env.filters["india_local"] = format_india_local

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

    @app.context_processor
    def inject_notification_activity():
        if not current_user.is_authenticated:
            return {}
        from models.campaign import Campaign
        return {
            "notification_items": Campaign.query.order_by(Campaign.created_at.desc()).limit(5).all()
        }

    # --------------------------------
    # Register Blueprints
    # --------------------------------
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.email import email_bp
    from models.campaign import Campaign, CampaignAttachment, CampaignRecipient, Suppression
    from models.sender_email import SenderEmail

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
        _ = (Campaign, CampaignAttachment, CampaignRecipient, Suppression, SenderEmail)
        sender_columns = {column["name"] for column in inspect(db.engine).get_columns("sender_emails")}
        sender_migrations = {
            "signoff": "TEXT NOT NULL DEFAULT ''",
            "smtp_server": "VARCHAR(255)",
            "smtp_port": "INTEGER",
            "smtp_use_tls": "BOOLEAN NOT NULL DEFAULT 1",
            "smtp_username": "VARCHAR(255)",
            "smtp_password_encrypted": "TEXT",
        }
        for column, sql_type in sender_migrations.items():
            if column not in sender_columns:
                with db.engine.begin() as connection:
                    connection.execute(text(f"ALTER TABLE sender_emails ADD COLUMN {column} {sql_type}"))
        # Keep existing SQLite installations compatible with the sender selection.
        if "sender_email" not in {column["name"] for column in inspect(db.engine).get_columns("campaigns")}:
            with db.engine.begin() as connection:
                connection.execute(text("ALTER TABLE campaigns ADD COLUMN sender_email VARCHAR(255)"))
        default_sender = app.config.get("MAIL_DEFAULT_SENDER")
        if default_sender and not SenderEmail.query.filter_by(email=default_sender).first():
            db.session.add(SenderEmail(email=default_sender))
            db.session.commit()

        # First-run desktop installs need an account even when no seed database
        # is available. Existing installations are left untouched.
        if User.query.count() == 0:
            import os
            default_admin_email = os.getenv(
                "DESFLYER_ADMIN_EMAIL", "admin@desflyer.com"
            ).strip().lower()
            default_admin_password = os.getenv(
                "DESFLYER_ADMIN_PASSWORD", "Admin@123"
            )
            default_admin_name = os.getenv(
                "DESFLYER_ADMIN_NAME", "DesFlyer Admin"
            ).strip() or "DesFlyer Admin"

            if default_admin_email and default_admin_password:
                admin = User(
                    name=default_admin_name,
                    email=default_admin_email,
                )
                admin.set_password(default_admin_password)
                db.session.add(admin)
                db.session.commit()

    return app


# --------------------------------
# Create Flask Application
# --------------------------------

app = create_app()


# --------------------------------
# Run Application
# --------------------------------

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5173, debug=False, use_reloader=False)
