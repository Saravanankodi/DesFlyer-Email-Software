from datetime import datetime

from models import db


class Campaign(db.Model):
    __tablename__ = "campaigns"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="QUEUED", index=True)
    total_recipients = db.Column(db.Integer, nullable=False, default=0)
    sent_count = db.Column(db.Integer, nullable=False, default=0)
    failed_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    recipients = db.relationship("CampaignRecipient", backref="campaign", lazy=True, cascade="all, delete-orphan")


class CampaignRecipient(db.Model):
    __tablename__ = "campaign_recipients"

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("campaigns.id"), nullable=False, index=True)
    email = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="PENDING", index=True)
    error_message = db.Column(db.Text)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    unsubscribe_token = db.Column(db.String(64), nullable=False, unique=True)
    email_log_id = db.Column(db.Integer, db.ForeignKey("email_logs.id"), nullable=False)
    sent_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Suppression(db.Model):
    __tablename__ = "suppression_list"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    reason = db.Column(db.String(30), nullable=False, default="UNSUBSCRIBED")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
