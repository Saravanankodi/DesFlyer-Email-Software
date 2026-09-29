from datetime import datetime

from models import db


class EmailLog(db.Model):

    __tablename__ = "email_logs"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    recipient = db.Column(
        db.String(255),
        nullable=False
    )

    cc = db.Column(
        db.Text,
        nullable=True
    )

    subject = db.Column(
        db.String(255),
        nullable=False
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="PENDING"
    )

    error_message = db.Column(
        db.Text,
        nullable=True
    )

    sent_at = db.Column(
        db.DateTime,
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.now
    )