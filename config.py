import os

from dotenv import load_dotenv


load_dotenv()


BASE_DIR = os.path.abspath(
    os.path.dirname(__file__)
)

DATABASE_DIR = os.path.join(
    BASE_DIR,
    "database"
)

os.makedirs(
    DATABASE_DIR,
    exist_ok=True
)


DATABASE_PATH = os.path.join(
    DATABASE_DIR,
    "desflyer.db"
)


class Config:

    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "desflyer-development-secret"
    )

    SQLALCHEMY_DATABASE_URI = (
        "sqlite:///"
        + DATABASE_PATH.replace("\\", "/")
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False


    # ==========================
    # EMAIL CONFIGURATION
    # ==========================

    MAIL_SERVER = os.getenv(
        "MAIL_SERVER"
    )

    MAIL_PORT = int(
        os.getenv(
            "MAIL_PORT",
            587
        )
    )

    MAIL_USE_TLS = (
        os.getenv(
            "MAIL_USE_TLS",
            "True"
        ).lower()
        == "true"
    )

    MAIL_USERNAME = os.getenv(
        "MAIL_USERNAME"
    )

    MAIL_PASSWORD = os.getenv(
        "MAIL_PASSWORD"
    )

    MAIL_DEFAULT_SENDER = os.getenv(
        "MAIL_DEFAULT_SENDER"
    )