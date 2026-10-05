import os
import sys
import secrets

from dotenv import load_dotenv


BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _is_frozen():
    return bool(getattr(sys, "frozen", False))


def _default_data_dir():
    # A one-file Windows executable is extracted to a temporary directory.
    # Keep the SQLite database and user configuration in a persistent location.
    if _is_frozen():
        app_data = os.getenv("LOCALAPPDATA") or os.path.expanduser("~/.local/share")
        return os.path.join(app_data, "DesFlyer")
    return BASE_DIR


DATA_DIR = os.path.abspath(os.getenv("DESFLYER_DATA_DIR", _default_data_dir()))
os.makedirs(DATA_DIR, exist_ok=True)

# Desktop users can keep configuration in %LOCALAPPDATA%/DesFlyer/.env.
# Development installations continue to support the project-root .env.
load_dotenv(os.path.join(DATA_DIR, ".env"), override=False)
load_dotenv(os.path.join(BASE_DIR, ".env"), override=False)

DATABASE_DIR = os.path.join(DATA_DIR, "database")
os.makedirs(DATABASE_DIR, exist_ok=True)
DATABASE_PATH = os.path.join(DATABASE_DIR, "desflyer.db")


def _sqlite_has_business_data(path):
    """Return True when a SQLite database already contains application data."""
    import sqlite3

    if not os.path.exists(path):
        return False

    try:
        with sqlite3.connect(path, timeout=2) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            if not tables:
                return False

            for table in (
                "users",
                "campaigns",
                "campaign_recipients",
                "email_logs",
                "sender_emails",
                "suppression",
            ):
                if table in tables:
                    count = connection.execute(
                        f"SELECT COUNT(*) FROM {table}"
                    ).fetchone()[0]
                    if count:
                        return True
    except (OSError, sqlite3.Error):
        # If the destination cannot be inspected safely, never overwrite it.
        return True

    return False


def _desktop_seed_database():
    """Seed a fresh packaged install from a nearby development database.

    The database is intentionally not bundled into the one-file executable.
    During development/build testing the existing database lives beside the
    project, so we can migrate it once into the persistent AppData location.
    If the executable is later distributed by itself, no seed is available and
    normal first-run admin initialization is used instead.
    """
    if not _is_frozen():
        return

    target = DATABASE_PATH
    if _sqlite_has_business_data(target):
        return

    executable_dir = os.path.dirname(os.path.abspath(sys.executable))
    candidates = [
        os.path.join(executable_dir, "database", "desflyer.db"),
        os.path.join(os.path.dirname(executable_dir), "database", "desflyer.db"),
        os.path.join(os.getcwd(), "database", "desflyer.db"),
    ]

    for source in candidates:
        source = os.path.abspath(source)
        if source == os.path.abspath(target) or not os.path.isfile(source):
            continue
        if not _sqlite_has_business_data(source):
            continue

        import shutil
        try:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copy2(source, target)
            return
        except OSError:
            # If migration cannot be performed, continue with a fresh database.
            return


_desktop_seed_database()


def _load_or_create_secret_key():
    configured = os.getenv("SECRET_KEY", "").strip()
    if configured:
        return configured
    key_path = os.path.join(DATA_DIR, "secret.key")
    try:
        with open(key_path, "r", encoding="utf-8") as handle:
            key = handle.read().strip()
        if key:
            return key
    except OSError:
        pass
    key = secrets.token_urlsafe(48)
    try:
        with open(key_path, "w", encoding="utf-8") as handle:
            handle.write(key)
    except OSError:
        # Development fallback; production/desktop normally has a writable data dir.
        pass
    return key


class Config:
    SECRET_KEY = _load_or_create_secret_key()

    SQLALCHEMY_DATABASE_URI = "sqlite:///" + DATABASE_PATH.replace("\\", "/")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAIL_SERVER = os.getenv("MAIL_SERVER")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "True").lower() == "true"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER")

    EMAIL_FOOTER_PHONE = os.getenv("EMAIL_FOOTER_PHONE", "").strip()
    EMAIL_FOOTER_WEBSITE = os.getenv("EMAIL_FOOTER_WEBSITE", "").strip()

    MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", 5 * 1024 * 1024))
    MAX_ATTACHMENT_BYTES = int(os.getenv("MAX_ATTACHMENT_BYTES", 18 * 1024 * 1024))
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_REQUEST_BYTES", 25 * 1024 * 1024))
    EMAIL_BATCH_SIZE = max(1, int(os.getenv("EMAIL_BATCH_SIZE", os.getenv("CAMPAIGN_BATCH_SIZE", 1))))
    EMAIL_SEND_DELAY = max(0, float(os.getenv("EMAIL_SEND_DELAY", os.getenv("CAMPAIGN_DELAY_SECONDS", 30))))
    EMAIL_MAX_RETRIES = max(0, int(os.getenv(
        "EMAIL_MAX_RETRIES", str(max(1, int(os.getenv("CAMPAIGN_MAX_ATTEMPTS", 3))) - 1)
    )))
    CAMPAIGN_BATCH_SIZE = EMAIL_BATCH_SIZE
    CAMPAIGN_DELAY_SECONDS = EMAIL_SEND_DELAY
    CAMPAIGN_MAX_ATTEMPTS = EMAIL_MAX_RETRIES + 1
    CAMPAIGN_POLL_SECONDS = float(os.getenv("CAMPAIGN_POLL_SECONDS", 2))
    CAMPAIGN_UNSUBSCRIBE_BASE_URL = os.getenv("CAMPAIGN_UNSUBSCRIBE_BASE_URL", "").strip()
