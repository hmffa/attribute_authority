import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from ..core.config import settings


def send_invitation_email(to: str, subject: str, body: str):
    msg = MIMEMultipart()
    msg["From"] = settings.SMTP_MAIL_SENDER
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html"))

    with smtplib.SMTP(settings.SMTP_MAIL_SERVER, settings.SMTP_MAIL_SERVER_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_MAIL_SERVER_USERNAME, settings.SMTP_MAIL_SERVER_PASSWORD)
        server.sendmail(settings.SMTP_MAIL_SENDER, to, msg.as_string())