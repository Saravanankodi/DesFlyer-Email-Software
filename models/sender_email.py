from datetime import datetime

from models import db


class SenderEmail(db.Model):
    __tablename__ = "sender_emails"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    signoff = db.Column(db.Text, nullable=False, default="")
    smtp_server = db.Column(db.String(255))
    smtp_port = db.Column(db.Integer)
    smtp_use_tls = db.Column(db.Boolean, nullable=False, default=True)
    smtp_username = db.Column(db.String(255))
    smtp_password_encrypted = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
