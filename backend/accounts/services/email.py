"""Email service for sending Magic Link emails via Brevo."""

import logging
import os

import requests

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def send_magic_link_email(email: str, token: str, school_name: str) -> bool:
    """Send a magic link email to the given address.

    In development (no BREVO_API_KEY), logs the link to console.
    In production, sends via Brevo transactional email API.

    Returns True if sent successfully (or logged in dev), False on failure.
    """
    api_key = os.environ.get("BREVO_API_KEY")
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    magic_link = f"{frontend_url}/claim/verify/{token}/"

    if not api_key:
        logger.info(
            "BREVO_API_KEY not set — logging magic link instead of sending email"
        )
        logger.info("Magic link for %s: %s", email, magic_link)
        return True

    payload = {
        "sender": {
            "name": "SJK(T) Connect",
            "email": "noreply@tamilschool.org.my",
        },
        "to": [{"email": email}],
        "subject": f"Verify your school page — {school_name}",
        "htmlContent": _build_email_html(magic_link, school_name),
    }

    try:
        response = requests.post(
            BREVO_API_URL,
            json=payload,
            headers={
                "api-key": api_key,
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        response.raise_for_status()
        logger.info("Magic link email sent to %s via Brevo", email)
        return True
    except requests.RequestException:
        logger.exception("Failed to send magic link email to %s", email)
        return False


def _build_email_html(magic_link: str, school_name: str) -> str:
    """Build the HTML body for the magic link email."""
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #4f46e5;">SJK(T) Connect</h2>
        <p>You requested to verify your school page for <strong>{school_name}</strong>.</p>
        <p>Click the button below to verify your email and claim your school page:</p>
        <p style="text-align: center; margin: 30px 0;">
            <a href="{magic_link}"
               style="background-color: #4f46e5; color: white; padding: 12px 24px;
                      text-decoration: none; border-radius: 6px; font-weight: bold;">
                Verify My Email
            </a>
        </p>
        <p style="color: #666; font-size: 14px;">
            This link expires in 24 hours. If you did not request this, you can safely ignore this email.
        </p>
        <p style="color: #666; font-size: 14px;">
            Or copy and paste this link into your browser:<br>
            <a href="{magic_link}" style="color: #4f46e5;">{magic_link}</a>
        </p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #999; font-size: 12px;">
            SJK(T) Connect — Tamil School Intelligence &amp; Advocacy Platform
        </p>
    </div>
    """
