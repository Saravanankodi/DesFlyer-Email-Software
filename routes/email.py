import json

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from flask_login import login_required
from sqlalchemy import or_, func

from models.email import EmailLog
from models import db
from models.campaign import Campaign, CampaignRecipient, Suppression
from services.email_service import send_email
from services.campaign_service import parse_upload, validate_values, queue_campaign, valid_email


email_bp = Blueprint(
    "email",
    __name__,
    url_prefix="/email"
)


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
                    values = parse_upload(upload)
                else:
                    values = request.form.get("recipients", "").split(",")
            except ValueError as error:
                flash(str(error), "error")
                return render_template("send_email.html", preview=None)
            preview = validate_values(values)
            subject = request.form.get("subject", "").strip()
            body = request.form.get("body", "")
            context = dict(preview=preview, recipient_source=source,
                recipients_input=request.form.get("recipients", ""), subject=subject,
                body=body, campaign_name=request.form.get("campaign_name", ""))
            if action == "preview":
                return render_template("send_email.html", **context)
            if action == "legacy_single":
                if source != "manual" or preview["invalid"] or len(preview["valid"]) != 1:
                    flash("Single email mode requires exactly one valid address.", "error")
                    return render_template("send_email.html", **context)
                if not subject or not body:
                    flash("Subject and message are required.", "error")
                    return render_template("send_email.html", **context)
                cc = [item.strip() for item in request.form.get("cc", "").split(",") if item.strip()]
                result = send_email(preview["valid"][0], subject, body, cc=cc)
                flash(result["message"], "success" if result["success"] else "error")
                return redirect(url_for("email.send"))
            if not subject or not body:
                flash("Subject and message are required.", "error")
                return render_template("send_email.html", **context)
            if preview["invalid"] and request.form.get("exclude_invalid") != "yes":
                flash("Correct or remove invalid addresses before queueing the campaign.", "error")
                return render_template("send_email.html", **context)
            if not preview["valid"]:
                flash("No valid recipients were provided.", "error")
                return render_template("send_email.html", **context)
            if not request.form.get("authorized_list"):
                flash("Confirm that recipients opted in to receive these emails.", "error")
                return render_template("send_email.html", **context)
            campaign, suppressed = queue_campaign(request.form.get("campaign_name", "Campaign").strip() or "Campaign",
                                                   subject, body, preview["valid"])
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
                "send_email.html"
            )

        # Convert CC input into a list
        cc = []

        if cc_input:

            cc = [
                email.strip()
                for email in cc_input.split(",")
                if email.strip()
            ]

        # Send email
        result = send_email(
            recipient=recipient,
            subject=subject,
            body=body,
            cc=cc
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
        "send_email.html", preview=None
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
    return render_template("campaign_detail.html", campaign=campaign, recipients=recipients, counts=counts, progress=progress)


@email_bp.route("/campaigns/<int:campaign_id>/progress")
@login_required
def campaign_progress(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    counts = {status.lower(): CampaignRecipient.query.filter_by(campaign_id=campaign.id, status=status).count()
              for status in ("PENDING", "SENDING", "SENT", "FAILED")}
    return {"status": campaign.status, "total": campaign.total_recipients, **counts}


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
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                EmailLog.recipient.ilike(search_term),
                EmailLog.subject.ilike(search_term)
            )
        )

    if status in {"SENT", "FAILED", "PENDING"}:
        query = query.filter(EmailLog.status == status)

    emails = query.order_by(
        EmailLog.created_at.desc()
    ).all()

    return render_template(
        "email_history.html",
        emails=emails
    )


@email_bp.route("/history/<int:email_id>")
@login_required
def email_detail(email_id):

    email = EmailLog.query.get_or_404(
        email_id
    )

    return render_template(
        "email_detail.html",
        email=email
    )
