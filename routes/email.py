from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from flask_login import login_required
from sqlalchemy import or_

from models.email import EmailLog
from services.email_service import send_email


email_bp = Blueprint(
    "email",
    __name__,
    url_prefix="/email"
)


@email_bp.route("/send", methods=["GET", "POST"])
@login_required
def send():

    if request.method == "POST":

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
        "send_email.html"
    )


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
