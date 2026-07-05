"""
Email service — sends transactional emails via SMTP.

Falls back to logging the email content when SMTP is not configured
(useful for local dev — check your console for the verification link).
"""
from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import get_settings

settings = get_settings()
log = logging.getLogger(__name__)


def _smtp_configured() -> bool:
    return bool(settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD)


def _send_email(to: str, subject: str, html_body: str, text_body: str) -> None:
    if not _smtp_configured():
        # Dev fallback: log the email so the developer can copy the link
        log.info(
            f"\n{'='*60}\n"
            f"[EMAIL NOT SENT — SMTP not configured]\n"
            f"To: {to}\n"
            f"Subject: {subject}\n"
            f"Body:\n{text_body}\n"
            f"{'='*60}"
        )
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = to
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.EMAIL_FROM, to, msg.as_string())


async def send_verification_email(email: str, name: str, token: str) -> None:
    verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    subject = "Verify your Lakshya AI account"
    text_body = (
        f"Hi {name},\n\n"
        f"Please verify your email by visiting:\n{verify_url}\n\n"
        f"This link expires in 24 hours.\n\n"
        f"If you did not create an account, you can ignore this email.\n\n"
        f"— Lakshya AI"
    )
    html_body = f"""
    <html><body>
    <p>Hi {name},</p>
    <p>Please verify your email address to activate your Lakshya AI account:</p>
    <p><a href="{verify_url}" style="background:#4f46e5;color:#fff;padding:10px 20px;
       border-radius:6px;text-decoration:none;display:inline-block;">Verify Email</a></p>
    <p>Or copy this link: <code>{verify_url}</code></p>
    <p>This link expires in 24 hours.</p>
    <p>— Lakshya AI</p>
    </body></html>
    """
    _send_email(email, subject, html_body, text_body)


async def send_password_reset_email(email: str, name: str, token: str) -> None:
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    subject = "Reset your Lakshya AI password"
    text_body = (
        f"Hi {name},\n\n"
        f"Someone requested a password reset for your account.\n"
        f"Visit this link to reset your password:\n{reset_url}\n\n"
        f"This link expires in 1 hour.\n\n"
        f"If you did not request this, you can safely ignore this email.\n\n"
        f"— Lakshya AI"
    )
    html_body = f"""
    <html><body>
    <p>Hi {name},</p>
    <p>Someone requested a password reset for your Lakshya AI account.</p>
    <p><a href="{reset_url}" style="background:#dc2626;color:#fff;padding:10px 20px;
       border-radius:6px;text-decoration:none;display:inline-block;">Reset Password</a></p>
    <p>Or copy this link: <code>{reset_url}</code></p>
    <p>This link expires in 1 hour.</p>
    <p>If you did not request this, you can safely ignore this email.</p>
    <p>— Lakshya AI</p>
    </body></html>
    """
    _send_email(email, subject, html_body, text_body)
