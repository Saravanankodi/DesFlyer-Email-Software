import json
import mimetypes

from flask import (
    Blueprint,
    current_app,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from flask_login import login_required
from sqlalchemy import func
from markupsafe import escape
from werkzeug.utils import secure_filename

from models.email import EmailLog
from models import db
from models.campaign import Campaign, CampaignRecipient, Suppression
from models.sender_email import SenderEmail
from services.email_service import send_email, encrypt_smtp_password
from services.campaign_service import parse_upload, validate_values, queue_campaign, valid_email, normalize_email_separators

email_bp = Blueprint(
    "email",
    __name__,
    url_prefix="/email"
)


def available_senders():
    return SenderEmail.query.order_by(SenderEmail.email).all()


def selected_sender():
    sender_id = request.form.get("sender_email_id", type=int)
    sender = db.session.get(SenderEmail, sender_id) if sender_id else None
    return sender.email if sender else None


def selected_signoff():
    sender_id = request.form.get("sender_email_id", type=int)
    sender = db.session.get(SenderEmail, sender_id) if sender_id else None
    return sender.signoff if sender else ""


def render_send(**context):
    context.setdefault("preview", None)
    context["senders"] = available_senders()
    context["selected_sender_id"] = request.form.get("sender_email_id", "")
    return render_template("send_email.html", **context)


def load_attachments():
    attachments = []
    total_bytes = 0
    for upload in request.files.getlist("attachments"):
        if not upload or not upload.filename:
            continue
        filename = secure_filename(upload.filename) or "attachment"
        data = upload.read()
        total_bytes += len(data)
        if total_bytes > current_app.config["MAX_ATTACHMENT_BYTES"]:
            raise ValueError("Attachments exceed the total upload size limit.")
        content_type = upload.mimetype or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        attachments.append({"filename": filename, "content_type": content_type, "data": data})
    return attachments


@email_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":
        action = request.form.get("action")
        address = request.form.get("email", "").strip()
        if action == "add":
            smtp_server = request.form.get("smtp_server", "").strip() or None
            smtp_username = request.form.get("smtp_username", "").strip() or None
            smtp_password = request.form.get("smtp_password", "")
            signoff = request.form.get("signoff", "").strip()
            try:
                smtp_port = int(request.form.get("smtp_port", "587"))
                if not 1 <= smtp_port <= 65535:
                    raise ValueError
            except ValueError:
                flash("SMTP port must be a number from 1 to 65535.", "error")
                return redirect(url_for("email.settings"))
            if not valid_email(address):
                flash("Enter a valid sender email address.", "error")
            elif not signoff:
                flash("Enter a sign-off for this sender email.", "error")
            elif SenderEmail.query.filter(func.lower(SenderEmail.email) == address.casefold()).first():
                flash("That sender email is already saved.", "error")
            else:
                if smtp_server and smtp_username and not smtp_password:
                    flash("Enter the SMTP password for this account.", "error")
                    return redirect(url_for("email.settings"))
                db.session.add(SenderEmail(
                    email=address,
                    signoff=signoff,
                    smtp_server=smtp_server,
                    smtp_port=smtp_port if smtp_server else None,
                    smtp_use_tls=request.form.get("smtp_use_tls") == "on",
                    smtp_username=smtp_username,
                    smtp_password_encrypted=encrypt_smtp_password(smtp_password) if smtp_password else None,
                ))
                db.session.commit()
                flash("Sender email added.", "success")
        elif action == "save_signoff":
            sender = db.session.get(SenderEmail, request.form.get("sender_id", type=int))
            signoff = request.form.get("signoff", "").strip()
            if sender and signoff:
                sender.signoff = signoff
                db.session.commit()
                flash("Sender sign-off updated.", "success")
            else:
                flash("Enter a sign-off before saving.", "error")
        elif action == "update":
            sender = db.session.get(SenderEmail, request.form.get("sender_id", type=int))
            address = request.form.get("email", "").strip()
            smtp_server = request.form.get("smtp_server", "").strip() or None
            smtp_username = request.form.get("smtp_username", "").strip() or None
            smtp_password = request.form.get("smtp_password", "")
            signoff = request.form.get("signoff", "").strip()
            try:
                smtp_port = int(request.form.get("smtp_port", "587"))
                if not 1 <= smtp_port <= 65535:
                    raise ValueError
            except ValueError:
                flash("SMTP port must be a number from 1 to 65535.", "error")
                return redirect(url_for("email.settings", edit=sender.id if sender else None))
            duplicate = SenderEmail.query.filter(func.lower(SenderEmail.email) == address.casefold()).first() if address else None
            if not sender:
                flash("Sender email not found.", "error")
            elif not valid_email(address):
                flash("Enter a valid sender email address.", "error")
            elif duplicate and duplicate.id != sender.id:
                flash("That sender email is already saved.", "error")
            elif not signoff:
                flash("Enter a sign-off for this sender email.", "error")
            elif smtp_server and smtp_username and not (smtp_password or sender.smtp_password_encrypted):
                flash("Enter the SMTP password for this account.", "error")
            else:
                sender.email = address
                sender.signoff = signoff
                sender.smtp_server = smtp_server
                sender.smtp_port = smtp_port if smtp_server else None
                sender.smtp_use_tls = request.form.get("smtp_use_tls") == "on"
                sender.smtp_username = smtp_username
                if smtp_password:
                    sender.smtp_password_encrypted = encrypt_smtp_password(smtp_password)
                elif not smtp_server:
                    sender.smtp_password_encrypted = None
                db.session.commit()
                flash("Sender email updated.", "success")
        elif action == "delete":
            sender = db.session.get(SenderEmail, request.form.get("sender_id", type=int))
            if sender:
                db.session.delete(sender)
                db.session.commit()
                flash("Sender email deleted.", "success")
        return redirect(url_for("email.settings"))
    edit_sender = db.session.get(SenderEmail, request.args.get("edit", type=int)) if request.args.get("edit", type=int) else None
    return render_template("settings.html", senders=available_senders(), edit_sender=edit_sender)


def append_user_footer(body, signoff):
    signoff = (signoff or "").strip()
    if not signoff:
        return body
    safe_signoff = str(escape(signoff)).replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")
    return f'{body}<br><br><div class="custom-email-footer">{safe_signoff}</div>'


@email_bp.route("/send", methods=["GET", "POST"])
@login_required
def send():

    if request.method == "POST":

        if request.form.get("recipient_source") in {"manual", "upload"}:
            source = request.form.get("recipient_source")
            action = request.form.get("action", "queue")
            try:
                if action == "queue" and request.form.get("validated_recipients"):
                    values = json.loads(request.form["validated_recipients"])
                    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
                        raise ValueError("Recipient preview was invalid. Validate the list again.")
                elif source == "upload":
                    upload = request.files.get("recipient_file")
                    if not upload or not upload.filename:
                        raise ValueError("Choose a CSV or .xlsx file first.")
                    upload.stream.seek(0, 2)
                    upload_size = upload.stream.tell()
                    upload.stream.seek(0)
                    if upload_size > current_app.config["MAX_UPLOAD_BYTES"]:
                        limit_mb = current_app.config["MAX_UPLOAD_BYTES"] / (1024 * 1024)
                        raise ValueError(f"Recipient files must be {limit_mb:g} MB or smaller.")
                    values = parse_upload(upload)
                else:
                    normalized_recipients = normalize_email_separators(request.form.get("recipients", ""))
                    values = normalized_recipients.split(",")
            except ValueError as error:
                flash(str(error), "error")
                return render_send(preview=None)
            preview = validate_values(values)
            subject = request.form.get("subject", "").strip()
            body = request.form.get("body", "")
            cc_input = request.form.get("cc", "").strip()
            cc_values = normalize_email_separators(cc_input).replace(";", ",").replace("\n", ",").split(",")
            cc = list(dict.fromkeys(address.strip() for address in cc_values if address.strip()))
            context = dict(preview=preview, recipient_source=source,
                recipients_input=normalize_email_separators(request.form.get("recipients", "")), subject=subject,
                body=body, campaign_name=request.form.get("campaign_name", ""), cc_input=cc_input)
            if action == "preview":
                return render_send(**context)
            if any(not valid_email(address) for address in cc):
                flash("Enter valid CC email addresses separated by commas or semicolons.", "error")
                return render_send(**context)
            if action == "legacy_single":
                if source != "manual" or preview["invalid"] or len(preview["valid"]) != 1:
                    flash("Single email mode requires exactly one valid address.", "error")
                    return render_send(**context)
                if not subject or not body:
                    flash("Subject and message are required.", "error")
                    return render_send(**context)
                try:
                    attachments = load_attachments()
                except ValueError as error:
                    flash(str(error), "error")
                    return render_send(**context)
                result = send_email(preview["valid"][0], subject, append_user_footer(body, selected_signoff()), cc=cc, sender=selected_sender(), attachments=attachments)
                flash(result["message"], "success" if result["success"] else "error")
                return redirect(url_for("email.send"))
            if not subject or not body:
                flash("Subject and message are required.", "error")
                return render_send(**context)
            if preview["invalid"] and request.form.get("exclude_invalid") != "yes":
                flash("Correct or remove invalid addresses before queueing the campaign.", "error")
                return render_send(**context)
            if not preview["valid"]:
                flash("No valid recipients were provided.", "error")
                return render_send(**context)
            if not request.form.get("authorized_list"):
                flash("Confirm that recipients opted in to receive these emails.", "error")
                return render_send(**context)
            try:
                attachments = load_attachments()
            except ValueError as error:
                flash(str(error), "error")
                return render_send(**context)
            campaign, suppressed = queue_campaign(request.form.get("campaign_name", "Campaign").strip() or "Campaign",
                                                   subject, append_user_footer(body, selected_signoff()), preview["valid"],
                                                   sender=selected_sender(), cc=cc, attachments=attachments)
            flash(f"Campaign queued with {campaign.total_recipients} recipients; {suppressed} suppressed address(es) excluded.", "success")
            return redirect(url_for("email.campaign_detail", campaign_id=campaign.id))

        recipient = request.form.get(
            "recipient",
            ""
        ).strip()

        subject = request.form.get(
            "subject",
            ""
        ).strip()

        cc_input = request.form.get(
            "cc",
            ""
        ).strip()

        body = request.form.get(
            "body",
            ""
        )

        # Validate required fields
        if not recipient or not subject or not body:

            flash(
                "Recipient, subject and message are required.",
                "error"
            )

            return render_template(
                "send_email.html", senders=available_senders(), selected_sender_id=request.form.get("sender_email_id", "")
            )

        # Convert CC input into a list
        cc = []

        if cc_input:
            cc_values = normalize_email_separators(cc_input).replace(";", ",").replace("\n", ",").split(",")
            cc = list(dict.fromkeys(email.strip() for email in cc_values if email.strip()))

        try:
            attachments = load_attachments()
        except ValueError as error:
            flash(str(error), "error")
            return render_send(preview=None)

        # Send email
        result = send_email(
            recipient=recipient,
            subject=subject,
            body=append_user_footer(body, selected_signoff()),
            cc=cc,
            sender=selected_sender(),
            attachments=attachments,
        )

        # Successful email
        if result["success"]:

            flash(
                result["message"],
                "success"
            )

            return redirect(
                url_for("email.send")
            )

        # Failed email
        flash(
            result["message"],
            "error"
        )

    return render_template(
        "send_email.html", preview=None, senders=available_senders(), selected_sender_id=""
    )


@email_bp.route("/campaigns")
@login_required
def campaigns():
    return render_template("campaign_history.html", campaigns=Campaign.query.order_by(Campaign.created_at.desc()).all())


@email_bp.route("/campaigns/<int:campaign_id>")
@login_required
def campaign_detail(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    recipients = CampaignRecipient.query.filter_by(campaign_id=campaign.id).order_by(CampaignRecipient.id).all()
    counts = {status: CampaignRecipient.query.filter_by(campaign_id=campaign.id, status=status).count()
              for status in ("PENDING", "SENDING", "SENT", "FAILED")}
    progress = round(counts["SENT"] / campaign.total_recipients * 100, 1) if campaign.total_recipients else 0
    delay_seconds = max(0, current_app.config.get("EMAIL_SEND_DELAY", 0))
    estimated_seconds = (counts["PENDING"] + counts["SENDING"]) * delay_seconds
    return render_template("campaign_detail.html", campaign=campaign, recipients=recipients, counts=counts,
                           progress=progress, estimated_seconds=estimated_seconds)


@email_bp.route("/campaigns/<int:campaign_id>/progress")
@login_required
def campaign_progress(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    counts = {status.lower(): CampaignRecipient.query.filter_by(campaign_id=campaign.id, status=status).count()
              for status in ("PENDING", "SENDING", "SENT", "FAILED")}
    delay_seconds = max(0, current_app.config.get("EMAIL_SEND_DELAY", 0))
    recipients = CampaignRecipient.query.filter_by(campaign_id=campaign.id).order_by(CampaignRecipient.id).all()
    return {
        "status": campaign.status,
        "total": campaign.total_recipients,
        "estimated_seconds": (counts["pending"] + counts["sending"]) * delay_seconds,
        **counts,
        "recipients": [{
            "email": recipient.email,
            "status": recipient.status,
            "attempts": recipient.attempts,
            "error": recipient.error_message,
            "sent_at": recipient.sent_at.isoformat() + "Z" if recipient.sent_at else None,
        } for recipient in recipients],
    }


@email_bp.route("/campaigns/<int:campaign_id>/control", methods=["POST"])
@login_required
def campaign_control(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    action = request.form.get("action")
    if action == "pause" and campaign.status in {"QUEUED", "RUNNING"}:
        campaign.status = "PAUSED"
    elif action == "resume" and campaign.status == "PAUSED":
        campaign.status = "QUEUED"
    db.session.commit()
    return redirect(url_for("email.campaign_detail", campaign_id=campaign.id))


@email_bp.route("/suppression", methods=["POST"])
@login_required
def add_suppression():
    address = request.form.get("email", "").strip()
    reason = request.form.get("reason", "").upper()
    if not valid_email(address):
        flash("Enter a valid email address.", "error")
    elif reason not in {"BOUNCE", "COMPLAINT", "UNSUBSCRIBED"}:
        flash("Choose a supported suppression reason.", "error")
    else:
        entry = Suppression.query.filter(func.lower(Suppression.email) == address.casefold()).first()
        if entry:
            entry.reason = reason
        else:
            db.session.add(Suppression(email=address.casefold(), reason=reason))
        db.session.commit()
        flash("Address added to the suppression list.", "success")
    return redirect(url_for("email.campaigns"))


@email_bp.route("/unsubscribe/<token>", methods=["GET", "POST"])
def unsubscribe(token):
    job = CampaignRecipient.query.filter_by(unsubscribe_token=token).first_or_404()
    if request.method == "POST":
        address = job.email.casefold()
        if not Suppression.query.filter(func.lower(Suppression.email) == address).first():
            db.session.add(Suppression(email=address, reason="UNSUBSCRIBED"))
            db.session.commit()
        return render_template("unsubscribe.html", completed=True)
    return render_template("unsubscribe.html", completed=False)


@email_bp.route("/history")
@login_required
def history():

    query = EmailLog.query
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "ALL").strip().upper()

    if search:
        query = query.filter(EmailLog.subject.ilike(f"%{search}%"))

    if status in {"SENT", "FAILED"}:
        query = query.filter(EmailLog.status == status)

    emails = query.order_by(
        EmailLog.created_at.desc()
    ).all()

    return render_template(
        "email_history.html",
        emails=emails,
    )


@email_bp.route("/history/<int:email_id>")
@login_required
def email_detail(email_id):

    email = EmailLog.query.get_or_404(
        email_id
    )
    from models.campaign import CampaignRecipient
    is_campaign_email = CampaignRecipient.query.filter_by(email_log_id=email.id).first() is not None

    return render_template(
        "email_detail.html",
        email=email,
        is_campaign_email=is_campaign_email,
    )
