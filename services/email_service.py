from datetime import datetime

from flask import current_app

from flask_mail import Mail, Message

from models import db
from models.email import EmailLog

mail = Mail()


def send_email(
    recipient,
    subject,
    body,
    cc=None
):

    email_log = EmailLog(
        recipient=recipient,
        subject=subject,
        cc=", ".join(cc) if cc else None,
        status="PENDING"
    )

    db.session.add(email_log)
    db.session.commit()


    try:

        message = Message(
            subject=subject,
            recipients=[recipient],
            cc=cc or [],
            sender=current_app.config[
                "MAIL_DEFAULT_SENDER"
            ]
        )


        message.html = body


        mail.send(message)


        email_log.status = "SENT"

        sent_at=datetime.now()

        db.session.commit()


        return {
            "success": True,
            "message": "Email sent successfully."
        }


    except Exception as error:

        email_log.status = "FAILED"
        email_log.error_message = str(error)

        db.session.commit()

        print("\n========== EMAIL ERROR ==========")
        print(type(error).__name__)
        print(str(error))
        print("=================================\n")

        return {
            "success": False,
            "message": f"Email could not be sent: {error}"
        }