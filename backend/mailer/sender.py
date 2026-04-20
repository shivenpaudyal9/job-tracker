"""
Gmail SMTP sender using an App Password (not OAuth).
Set up at: myaccount.google.com/apppasswords
Required env vars: GMAIL_USER, GMAIL_APP_PASSWORD
"""

import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def send_report(to_email: str, subject: str, html_content: str):
    gmail_user = os.environ["GMAIL_USER"]
    gmail_password = os.environ["GMAIL_APP_PASSWORD"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = to_email
    msg.attach(MIMEText(html_content, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, gmail_password)
        server.send_message(msg)

    logger.info("Email sent: '%s' → %s", subject, to_email)
