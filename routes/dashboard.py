from datetime import datetime, timedelta

from flask import Blueprint, render_template
from flask_login import login_required

from models import db
from models.email import EmailLog
from models.campaign import Campaign, CampaignRecipient


dashboard_bp = Blueprint(
    "dashboard",
    __name__,
    url_prefix="/dashboard"
)


@dashboard_bp.route("/")
@login_required
def dashboard():

    total_emails = EmailLog.query.count()

    sent_emails = EmailLog.query.filter_by(
        status="SENT"
    ).count()

    failed_emails = EmailLog.query.filter_by(
        status="FAILED"
    ).count()

    pending_emails = EmailLog.query.filter_by(
        status="PENDING"
    ).count()

    recent_emails = EmailLog.query.order_by(
        EmailLog.created_at.desc()
    ).limit(10).all()

    return render_template(
        "dashboard.html",
        total_emails=total_emails,
        sent_emails=sent_emails,
        failed_emails=failed_emails,
        pending_emails=pending_emails,
        recent_emails=recent_emails
    )


@dashboard_bp.route("/report")
@login_required
def report():
    return render_template("report.html")


@dashboard_bp.route("/analytics")
@login_required
def analytics():
    total_emails = EmailLog.query.count()
    sent_emails = EmailLog.query.filter_by(status="SENT").count()
    failed_emails = EmailLog.query.filter_by(status="FAILED").count()
    pending_emails = EmailLog.query.filter_by(status="PENDING").count()
    delivery_rate = round((sent_emails / total_emails) * 100) if total_emails else 0
    total_campaigns = Campaign.query.count()
    campaign_recipients = CampaignRecipient.query.count()
    campaign_sent = CampaignRecipient.query.filter_by(status="SENT").count()
    campaign_failed = CampaignRecipient.query.filter_by(status="FAILED").count()
    campaign_pending = CampaignRecipient.query.filter(CampaignRecipient.status.in_(["PENDING", "SENDING"])).count()
    campaign_success_rate = round(campaign_sent / campaign_recipients * 100, 1) if campaign_recipients else 0

    today = datetime.now().date()
    daily_activity = []
    for days_ago in range(6, -1, -1):
        day = today - timedelta(days=days_ago)
        count = EmailLog.query.filter(
            db.func.date(EmailLog.created_at) == day
        ).count()
        daily_activity.append({"label": day.strftime("%a"), "date": day.strftime("%d %b"), "count": count})

    peak = max((day["count"] for day in daily_activity), default=0)
    for day in daily_activity:
        day["height"] = round(day["count"] / peak * 100) if peak else 0

    return render_template(
        "analytics.html",
        total_emails=total_emails,
        sent_emails=sent_emails,
        failed_emails=failed_emails,
        pending_emails=pending_emails,
        delivery_rate=delivery_rate,
        daily_activity=daily_activity,
        total_campaigns=total_campaigns,
        campaign_recipients=campaign_recipients,
        campaign_sent=campaign_sent,
        campaign_failed=campaign_failed,
        campaign_pending=campaign_pending,
        campaign_success_rate=campaign_success_rate,
    )
