"""
Auto-responder for classified inbound emails.

Sends template-based acknowledgement responses via Brevo (production)
or logs to console (dev mode). Skips escalated and already-responded emails.

Uses the same Brevo transactional API pattern as broadcasts/services/sender.py.
"""

import logging
import os

import requests
from django.utils import timezone

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"

# Response templates by classification.
# {name} is replaced with the sender's name (or "there" if unknown).
RESPONSE_TEMPLATES = {
    "CORRECTION": (
        "Thank you for the correction, {name}. We take data accuracy seriously "
        "and will review and update our records accordingly. Your attention to "
        "detail helps us serve the Tamil school community better."
    ),
    "TIP": (
        "Thank you for the tip, {name}. We appreciate you sharing this "
        "information with us. Our team will look into it and may follow up "
        "if we need further details."
    ),
    "COMPLAINT": (
        "Thank you for reaching out, {name}. We have received your feedback "
        "and take all concerns seriously. A member of our team will review "
        "your message and respond as needed."
    ),
    "PRAISE": (
        "Thank you for the kind words, {name}! Feedback like yours motivates "
        "us to keep working for Tamil schools. We are glad our work is making "
        "a difference."
    ),
    "QUESTION": (
        "Thank you for your question, {name}. We have received it and will "
        "get back to you with an answer as soon as we can."
    ),
    "UNSUBSCRIBE": (
        "We have received your unsubscribe request, {name}. You will be "
        "removed from our mailing list shortly. If you change your mind, "
        "you can re-subscribe at any time via our website."
    ),
}


def auto_respond(email):
    """
    Send a template-based auto-response for a classified InboundEmail.

    Skips:
    - Escalated emails (human should handle these)
    - Already-responded emails (AUTO_RESPONDED or RESOLVED)
    - UNCLASSIFIED emails (not enough info to respond)

    Marks IRRELEVANT emails as RESOLVED without sending a response.

    Args:
        email: InboundEmail instance with classification set.
    """
    # Skip escalated emails — a human will handle these
    if email.escalated:
        logger.info("Skipping escalated email %s", email.gmail_message_id)
        return

    # Skip already-responded emails
    if email.response_status in ("AUTO_RESPONDED", "RESOLVED"):
        logger.info(
            "Skipping already-%s email %s",
            email.response_status.lower(),
            email.gmail_message_id,
        )
        return

    # Mark irrelevant emails as resolved without sending a response
    if email.classification == "IRRELEVANT":
        email.response_status = "RESOLVED"
        email.responded_at = timezone.now()
        email.save(update_fields=["response_status", "responded_at"])
        logger.info("Resolved irrelevant email %s", email.gmail_message_id)
        return

    # Skip unclassified emails — nothing meaningful to say yet
    if email.classification == "UNCLASSIFIED":
        logger.info("Skipping unclassified email %s", email.gmail_message_id)
        return

    # Build the response text from template
    template = RESPONSE_TEMPLATES.get(email.classification)
    if not template:
        logger.warning(
            "No template for classification '%s' on email %s",
            email.classification,
            email.gmail_message_id,
        )
        return

    name = email.from_name.split()[0] if email.from_name else "there"
    response_text = template.format(name=name)
    subject = f"Re: {email.subject}"

    # Send via Brevo or log in dev mode
    api_key = os.environ.get("BREVO_API_KEY")
    if api_key:
        _send_via_brevo(api_key, email, subject, response_text)
    else:
        logger.info(
            "DEV MODE — Auto-response for %s (%s): %s",
            email.gmail_message_id,
            email.classification,
            response_text[:100],
        )

    # Update email record
    email.response_status = "AUTO_RESPONDED"
    email.auto_response_text = response_text
    email.responded_at = timezone.now()
    email.save(
        update_fields=["response_status", "auto_response_text", "responded_at"]
    )

    logger.info(
        "Auto-responded to email %s (%s)",
        email.gmail_message_id,
        email.classification,
    )


def _send_via_brevo(api_key, email, subject, response_text):
    """
    Send an auto-response email via Brevo transactional API.

    Args:
        api_key: Brevo API key.
        email: InboundEmail instance (for recipient details).
        subject: Email subject line.
        response_text: Plain text response body.
    """
    payload = {
        "sender": {
            "name": "SJK(T) Connect",
            "email": "feedback@tamilschool.org",
        },
        "replyTo": {
            "email": "feedback@tamilschool.org",
            "name": "SJK(T) Connect",
        },
        "to": [
            {
                "email": email.from_email,
                "name": email.from_name or email.from_email,
            }
        ],
        "subject": subject,
        "textContent": response_text,
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
        logger.info(
            "Brevo auto-response sent to %s (message: %s)",
            email.from_email,
            response.json().get("messageId", ""),
        )
    except requests.RequestException:
        logger.exception(
            "Failed to send auto-response to %s via Brevo",
            email.from_email,
        )
