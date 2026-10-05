from datetime import datetime, timedelta

from flask import Blueprint, render_template
from flask_login import login_required

from models import db
from models.email import EmailLog
from models.campaign import Campaign, CampaignRecipient, Suppression


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

    recent_emails = EmailLog.query.order_by(
        EmailLog.created_at.desc()
    ).limit(10).all()

    return render_template(
        "dashboard.html",
        total_emails=total_emails,
        sent_emails=sent_emails,
        failed_emails=failed_emails,
        recent_emails=recent_emails
    )


@dashboard_bp.route("/report")
@login_required
def report():
    final_statuses = ("SENT", "FAILED")
    sent_count = EmailLog.query.filter_by(status="SENT").count()
    failed_count = EmailLog.query.filter_by(status="FAILED").count()
    total_results = sent_count + failed_count
    emails = EmailLog.query.filter(EmailLog.status.in_(final_statuses)).order_by(
        db.func.coalesce(EmailLog.sent_at, EmailLog.created_at).desc()
    ).limit(200).all()
    email_ids = [email.id for email in emails]
    campaign_names = dict(db.session.query(
        CampaignRecipient.email_log_id, Campaign.name
    ).join(Campaign, Campaign.id == CampaignRecipient.campaign_id).filter(
        CampaignRecipient.email_log_id.in_(email_ids)
    ).all()) if email_ids else {}
    bounce_suppressions = Suppression.query.filter_by(reason="BOUNCE").order_by(
        Suppression.created_at.desc()
    ).limit(100).all()
    bounce_suppression_count = Suppression.query.filter_by(reason="BOUNCE").count()
    return render_template(
        "report.html",
        emails=emails,
        campaign_names=campaign_names,
        total_results=total_results,
        sent_count=sent_count,
        failed_count=failed_count,
        bounce_suppression_count=bounce_suppression_count,
        bounce_suppressions=bounce_suppressions,
    )


@dashboard_bp.route("/analytics")
@login_required
def analytics():
    final_statuses = ("SENT", "FAILED")
    final_emails = EmailLog.query.filter(EmailLog.status.in_(final_statuses)).all()
    sent_count = sum(email.status == "SENT" for email in final_emails)
    failed_count = sum(email.status == "FAILED" for email in final_emails)
    total_results = sent_count + failed_count
    success_rate = round(sent_count / total_results * 100, 1) if total_results else 0
    failure_rate = round(failed_count / total_results * 100, 1) if total_results else 0
    bounce_suppression_count = Suppression.query.filter_by(reason="BOUNCE").count()

    # EmailLog.created_at is the project's local log timestamp; use it for consistent trends.
    now = datetime.now()
    today = now.date()
    daily_start = today - timedelta(days=13)
    trend_emails = [email for email in final_emails if email.created_at and email.created_at.date() >= daily_start]
    daily_counts = {}
    for email in trend_emails:
        day = email.created_at.date()
        daily_counts[day] = daily_counts.get(day, 0) + 1
    daily_activity = [{
        "label": (today - timedelta(days=days_ago)).strftime("%d"),
        "date": (today - timedelta(days=days_ago)).strftime("%d %b"),
        "count": daily_counts.get(today - timedelta(days=days_ago), 0),
    } for days_ago in range(6, -1, -1)]
    daily_peak = max((day["count"] for day in daily_activity), default=0)
    for day in daily_activity:
        day["height"] = round(day["count"] / daily_peak * 100) if daily_peak else 0

    month_starts = [datetime(now.year, month, 1) for month in range(1, now.month + 1)]
    monthly_counts = {month.date(): 0 for month in month_starts}
    for email in final_emails:
        if not email.created_at:
            continue
        month = email.created_at.replace(day=1, hour=0, minute=0, second=0, microsecond=0).date()
        if month in monthly_counts:
            monthly_counts[month] += 1
    monthly_activity = [{
        "label": month.strftime("%b"),
        "date": month.strftime("%B %Y"),
        "count": monthly_counts[month.date()],
    } for month in month_starts]
    monthly_peak = max((month["count"] for month in monthly_activity), default=0)
    for month in monthly_activity:
        month["height"] = round(month["count"] / monthly_peak * 100) if monthly_peak else 0

    domains = {}
    for email in final_emails:
        domain = email.recipient.rsplit("@", 1)[-1].casefold() if "@" in email.recipient else "Unknown"
        metrics = domains.setdefault(domain, {"sent": 0, "failed": 0})
        metrics[email.status.casefold()] += 1
    domain_performance = [{
        "domain": domain,
        "sent": metrics["sent"],
        "failed": metrics["failed"],
        "total": metrics["sent"] + metrics["failed"],
        "success_rate": round(metrics["sent"] / (metrics["sent"] + metrics["failed"]) * 100, 1),
    } for domain, metrics in domains.items()]
    domain_performance.sort(key=lambda item: (-item["total"], item["domain"]))
    domain_performance = domain_performance[:8]

    campaign_status_rows = db.session.query(
        Campaign.id, Campaign.name, Campaign.subject, Campaign.created_at,
        CampaignRecipient.status, db.func.count(CampaignRecipient.id)
    ).join(CampaignRecipient, CampaignRecipient.campaign_id == Campaign.id).filter(
        CampaignRecipient.status.in_(final_statuses)
    ).group_by(Campaign.id, Campaign.name, Campaign.subject, Campaign.created_at, CampaignRecipient.status).all()
    campaign_metrics = {}
    for campaign_id, name, subject, created_at, status, count in campaign_status_rows:
        campaign = campaign_metrics.setdefault(campaign_id, {
            "name": name, "subject": subject, "created_at": created_at,
            "sent": 0, "failed": 0,
        })
        campaign[status.casefold()] = count
    campaign_performance = []
    for campaign in campaign_metrics.values():
        campaign["total"] = campaign["sent"] + campaign["failed"]
        campaign["success_rate"] = round(campaign["sent"] / campaign["total"] * 100, 1) if campaign["total"] else 0
        campaign_performance.append(campaign)
    campaign_performance.sort(key=lambda item: item["created_at"], reverse=True)
    campaign_performance = campaign_performance[:10]

    return render_template(
        "analytics.html",
        total_results=total_results,
        sent_count=sent_count,
        failed_count=failed_count,
        success_rate=success_rate,
        failure_rate=failure_rate,
        bounce_suppression_count=bounce_suppression_count,
        sent_share=round(sent_count / total_results * 100, 1) if total_results else 0,
        failed_share=round(failed_count / total_results * 100, 1) if total_results else 0,
        daily_activity=daily_activity,
        monthly_activity=monthly_activity,
        domain_performance=domain_performance,
        campaign_performance=campaign_performance,
        recent_week_count=sum(daily_counts.get(today - timedelta(days=days_ago), 0) for days_ago in range(6, -1, -1)),
        prior_week_count=sum(daily_counts.get(today - timedelta(days=days_ago), 0) for days_ago in range(13, 6, -1)),
        weekly_change=(
            sum(daily_counts.get(today - timedelta(days=days_ago), 0) for days_ago in range(6, -1, -1))
            - sum(daily_counts.get(today - timedelta(days=days_ago), 0) for days_ago in range(13, 6, -1))
        ),
    )
