import csv
import io
import re
import smtplib
import time
import uuid
from datetime import datetime
from email.utils import parseaddr

from flask import current_app
from flask_mail import Message
from sqlalchemy import func

from models import db
from models.campaign import Campaign, CampaignRecipient, Suppression
from models.email import EmailLog
from services.email_service import mail

EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$")
EMAIL_HEADERS = {"email", "e-mail", "emailaddress", "email_address", "mail"}


def valid_email(value):
    value = value.strip()
    _, parsed = parseaddr(value)
    return parsed == value and len(value) <= 254 and bool(EMAIL_PATTERN.fullmatch(value))


def validate_values(values):
    valid, invalid, duplicates = [], [], []
    seen = set()
    for value in values:
        address = (value or "").strip()
        if not address:
            continue
        if not valid_email(address):
            invalid.append(address)
            continue
        key = address.casefold()
        if key in seen:
            duplicates.append(address)
        else:
            seen.add(key)
            valid.append(address)
    return {"valid": valid, "invalid": invalid, "duplicates": duplicates}


def parse_upload(file):
    filename = (file.filename or "").lower()
    if not filename.endswith((".csv", ".xlsx")):
        raise ValueError("Choose a .csv or .xlsx file. Legacy .xls is not supported.")
    try:
        if filename.endswith(".csv"):
            content = file.stream.read().decode("utf-8-sig")
            rows = list(csv.reader(io.StringIO(content)))
        else:
            from openpyxl import load_workbook
            workbook = load_workbook(file, read_only=True, data_only=True)
            sheet = workbook.active
            rows = [list(row) for row in sheet.iter_rows(values_only=True)]
            workbook.close()
    except Exception as exc:
        raise ValueError("Could not read this file. Check that it is a valid UTF-8 CSV or .xlsx workbook.") from exc
    rows = [["" if value is None else str(value).strip() for value in row] for row in rows]
    rows = [row for row in rows if any(row)]
    if not rows:
        raise ValueError("The uploaded file is empty.")
    headers = [re.sub(r"[^a-z0-9_ -]", "", cell.casefold()).replace(" ", "") for cell in rows[0]]
    candidates = [i for i, header in enumerate(headers) if header in EMAIL_HEADERS or header.replace("_", "").replace("-", "") in EMAIL_HEADERS]
    if candidates:
        index = candidates[0]
        return [row[index] if index < len(row) else "" for row in rows[1:]]
    # A single-column file may be a headerless list; the first row is skipped as a header only when it says email.
    if len(rows[0]) == 1 and rows[0][0].casefold() not in EMAIL_HEADERS:
        return [row[0] for row in rows]
    raise ValueError("No recognizable email column found. Add a column named email.")


def suppressed_addresses(addresses):
    if not addresses:
        return set()
    suppressed = set()
    normalized = list({address.casefold() for address in addresses})
    # Keep SQLite expression/parameter counts bounded for large campaigns.
    for start in range(0, len(normalized), 500):
        chunk = normalized[start:start + 500]
        suppressed.update(email for (email,) in db.session.query(Suppression.email).filter(
            func.lower(Suppression.email).in_(chunk)
        ).all())
    return {email.casefold() for email in suppressed}


def queue_campaign(name, subject, body, recipients):
    suppressed = suppressed_addresses(recipients)
    allowed = [email for email in recipients if email.casefold() not in suppressed]
    campaign = Campaign(name=name[:255], subject=subject, body=body, status="QUEUED", total_recipients=len(allowed))
    db.session.add(campaign)
    db.session.flush()
    logs = [EmailLog(recipient=address, subject=subject, status="PENDING") for address in allowed]
    db.session.add_all(logs)
    db.session.flush()
    jobs = [CampaignRecipient(campaign_id=campaign.id, email=address,
        unsubscribe_token=uuid.uuid4().hex, email_log_id=log.id)
        for address, log in zip(allowed, logs)]
    db.session.add_all(jobs)
    db.session.commit()
    return campaign, len(recipients) - len(allowed)


def process_campaign(campaign_id):
    campaign = db.session.get(Campaign, campaign_id)
    if not campaign or campaign.status not in {"QUEUED", "RUNNING"}:
        return
    campaign.status = "RUNNING"
    campaign.started_at = campaign.started_at or datetime.utcnow()
    db.session.commit()
    batch_size = max(1, current_app.config["CAMPAIGN_BATCH_SIZE"])
    delay = max(0, current_app.config["CAMPAIGN_DELAY_SECONDS"])
    max_attempts = max(1, current_app.config["CAMPAIGN_MAX_ATTEMPTS"])
    while True:
        jobs = CampaignRecipient.query.filter_by(campaign_id=campaign_id, status="PENDING").order_by(CampaignRecipient.id).limit(batch_size).all()
        if not jobs:
            break
        for job in jobs:
            campaign = db.session.get(Campaign, campaign_id)
            if not campaign or campaign.status == "PAUSED":
                return
            job.status = "SENDING"
            job.attempts += 1
            db.session.commit()
            try:
                unsubscribe_url = current_app.config.get("CAMPAIGN_UNSUBSCRIBE_BASE_URL", "http://localhost:5000")
                link = unsubscribe_url.rstrip("/") + "/email/unsubscribe/" + job.unsubscribe_token
                msg = Message(subject=campaign.subject, recipients=[job.email], sender=current_app.config["MAIL_DEFAULT_SENDER"])
                msg.html = campaign.body + f'<hr><p><a href="{link}">Unsubscribe</a> from these marketing emails.</p>'
                msg.extra_headers = {"List-Unsubscribe": f"<{link}>", "List-Unsubscribe-Post": "List-Unsubscribe=One-Click"}
                mail.send(msg)
                job.status = "SENT"
                job.sent_at = datetime.utcnow()
                job.error_message = None
                EmailLog.query.get(job.email_log_id).status = "SENT"
                EmailLog.query.get(job.email_log_id).sent_at = datetime.utcnow()
                campaign.sent_count += 1
            except Exception as exc:
                job.error_message = f"{type(exc).__name__}: {exc}"[:2000]
                permanent_smtp_error = isinstance(exc, smtplib.SMTPResponseException) and 500 <= exc.smtp_code < 600
                if job.attempts < max_attempts and not permanent_smtp_error:
                    job.status = "PENDING"
                    db.session.commit()
                    if delay:
                        time.sleep(delay)
                    continue
                job.status = "FAILED"
                log = db.session.get(EmailLog, job.email_log_id)
                log.status = "FAILED"
                log.error_message = job.error_message
                campaign.failed_count += 1
            db.session.commit()
            if delay:
                time.sleep(delay)
        if db.session.get(Campaign, campaign_id).status == "PAUSED":
            return
        campaign = db.session.get(Campaign, campaign_id)
    campaign.sent_count = CampaignRecipient.query.filter_by(campaign_id=campaign_id, status="SENT").count()
    campaign.failed_count = CampaignRecipient.query.filter_by(campaign_id=campaign_id, status="FAILED").count()
    campaign.status = "COMPLETED"
    campaign.completed_at = datetime.utcnow()
    db.session.commit()


def run_worker(app):
    with app.app_context():
        # Recover campaigns interrupted by worker shutdown; SENDING jobs become eligible again.
        CampaignRecipient.query.filter_by(status="SENDING").update({"status": "PENDING"})
        Campaign.query.filter_by(status="RUNNING").update({"status": "QUEUED"})
        db.session.commit()
    while True:
        with app.app_context():
            campaign = Campaign.query.filter_by(status="QUEUED").order_by(Campaign.created_at).first()
            if campaign:
                try:
                    process_campaign(campaign.id)
                except Exception:
                    db.session.rollback()
                    campaign = db.session.get(Campaign, campaign.id)
                    if campaign:
                        campaign.status = "FAILED"
                        db.session.commit()
            else:
                time.sleep(max(0.2, app.config["CAMPAIGN_POLL_SECONDS"]))
