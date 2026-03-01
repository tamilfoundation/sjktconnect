"""Service for sending outreach emails to schools via Brevo."""

import logging
import os

import requests
from django.utils import timezone

from outreach.models import OutreachEmail
from schools.models import School

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def send_outreach_email(school: School, recipient_email: str) -> OutreachEmail:
    """Send an introduction/outreach email to a school.

    In development (no BREVO_API_KEY), logs to console and marks as SENT.
    In production, sends via Brevo transactional email API.

    Returns the OutreachEmail record.
    """
    api_key = os.environ.get("BREVO_API_KEY")
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    school_url = f"{frontend_url}/school/{school.moe_code}"
    claim_url = f"{frontend_url}/claim/?school={school.moe_code}"
    subject = f"Your school page is ready - {school.short_name or school.name}"

    record = OutreachEmail.objects.create(
        school=school,
        recipient_email=recipient_email,
        subject=subject,
        status=OutreachEmail.Status.PENDING,
    )

    if not api_key:
        logger.info(
            "BREVO_API_KEY not set — logging outreach email instead of sending"
        )
        logger.info(
            "Outreach email for %s (%s): school page %s, claim %s",
            school.moe_code, recipient_email, school_url, claim_url,
        )
        record.status = OutreachEmail.Status.SENT
        record.sent_at = timezone.now()
        record.save()
        return record

    payload = {
        "sender": {
            "name": "SJK(T) Connect",
            "email": "noreply@tamilschool.org",
        },
        "to": [{"email": recipient_email}],
        "subject": subject,
        "htmlContent": _build_outreach_html(school, school_url, claim_url),
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
        data = response.json()
        record.status = OutreachEmail.Status.SENT
        record.sent_at = timezone.now()
        record.brevo_message_id = data.get("messageId", "")
        record.save()
        logger.info("Outreach email sent to %s for %s", recipient_email, school.moe_code)
    except requests.RequestException as exc:
        record.status = OutreachEmail.Status.FAILED
        record.error_message = str(exc)
        record.save()
        logger.exception("Failed to send outreach email to %s", recipient_email)

    return record


def _build_outreach_html(school: School, school_url: str, claim_url: str) -> str:
    """Build the HTML body for the outreach introduction email."""
    school_name = school.short_name or school.name
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #4f46e5;">SJK(T) Connect</h2>
        <p>Dear Headmaster/Headmistress,</p>
        <p>We are pleased to inform you that a dedicated school page has been created for
        <strong>{school_name}</strong> on <strong>SJK(T) Connect</strong> &mdash; Malaysia's
        Tamil school intelligence and advocacy platform.</p>
        <p>Your school page includes:</p>
        <ul>
            <li>School profile with enrolment data and location</li>
            <li>Parliamentary constituency and representative information</li>
            <li>Parliament Watch &mdash; tracking how your MP speaks about Tamil schools</li>
        </ul>
        <p style="text-align: center; margin: 30px 0;">
            <a href="{school_url}"
               style="background-color: #4f46e5; color: white; padding: 12px 24px;
                      text-decoration: none; border-radius: 6px; font-weight: bold;">
                View Your School Page
            </a>
        </p>
        <p>You can also <strong>claim your school page</strong> to verify and update your
        school's information:</p>
        <p style="text-align: center; margin: 20px 0;">
            <a href="{claim_url}"
               style="background-color: #059669; color: white; padding: 10px 20px;
                      text-decoration: none; border-radius: 6px; font-weight: bold;">
                Claim Your School Page
            </a>
        </p>
        <p style="color: #666; font-size: 14px;">
            To claim your page, you'll need your school's official MOE email address
            ({school.moe_code.lower()}@moe.edu.my). A verification link will be sent to
            that address.
        </p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #999; font-size: 12px;">
            SJK(T) Connect &mdash; Tamil School Intelligence &amp; Advocacy Platform<br>
            An initiative of the Malaysian Community Education Foundation (MCEF)
        </p>
    </div>
    """
