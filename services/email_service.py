import base64
import hashlib
import smtplib
import ssl

from flask import current_app

from flask_mail import Mail

mail = Mail()


def _credential_cipher():
    # Derive a stable Fernet key from SECRET_KEY; SMTP passwords remain encrypted at rest.
    from cryptography.fernet import Fernet
    key = base64.urlsafe_b64encode(hashlib.sha256(current_app.config["SECRET_KEY"].encode("utf-8")).digest())
    return Fernet(key)


def encrypt_smtp_password(password):
    return _credential_cipher().encrypt(password.encode("utf-8")).decode("ascii") if password else None


def decrypt_smtp_password(token):
    return _credential_cipher().decrypt(token.encode("ascii")).decode("utf-8") if token else None


def send_message(message, sender_record=None):
    """Send through a sender-specific SMTP account, or the legacy app account."""
    if not sender_record or not sender_record.smtp_server:
        mail.send(message)
        return
    host = sender_record.smtp_server
    port = sender_record.smtp_port or 587
    password = decrypt_smtp_password(sender_record.smtp_password_encrypted)
    context = ssl.create_default_context()
    with smtplib.SMTP(host, port, timeout=30) as connection:
        connection.ehlo()
        if sender_record.smtp_use_tls:
            connection.starttls(context=context)
            connection.ehlo()
        if sender_record.smtp_username:
            connection.login(sender_record.smtp_username, password or "")
        connection.sendmail(message.sender, message.recipients + message.cc, message.as_bytes())


def sender_record_for_address(address):
    from models.sender_email import SenderEmail
    from models import db
    if not address:
        return None
    return db.session.query(SenderEmail).filter(db.func.lower(SenderEmail.email) == address.casefold()).first()


def add_email_footer(body):
    """Append the shared DesFlyer sign-off to an HTML email body."""
    # A user supplied sign-off replaces the shared default footer to avoid duplicates.
    if 'class="custom-email-footer"' in (body or ""):
        return body
    lines = ["Regards", "DesFlyer"]
    phone = current_app.config.get("EMAIL_FOOTER_PHONE")
    website = current_app.config.get("EMAIL_FOOTER_WEBSITE")
    if phone:
        lines.append(f"Phone: {phone}")
    if website:
        lines.append(f'Website: <a href="{website}">{website}</a>')
    footer = "<br>".join(lines)
    return f'{body or ""}<br><br><div class="email-footer">{footer}</div>'


def send_email(
    recipient,
    subject,
    body,
    cc=None,
    sender=None,
    attachments=None,
):
    try:
        from services.campaign_service import queue_campaign, valid_email

        if not valid_email(recipient):
            return {"success": False, "message": "Enter a valid recipient email address."}
        cc = cc or []
        if any(not valid_email(address) for address in cc):
            return {"success": False, "message": "One or more CC addresses are invalid."}
        campaign, suppressed = queue_campaign(
            "Single email", subject, body, [recipient], sender=sender, cc=cc,
            attachments=attachments,
        )
        if campaign.total_recipients == 0:
            return {"success": False, "message": "This recipient is suppressed and was not queued."}
        return {
            "success": True,
            "message": "Email queued for sending." if not suppressed else "Email could not be queued."
        }
    except Exception as error:
        return {
            "success": False,
            "message": f"Email could not be queued: {error}"
        }
