"""
Service for sending broadcast emails via Brevo transactional API.

Handles status transitions (DRAFT -> SENDING -> SENT), per-recipient
tracking, rate limiting, and dev-mode console fallback.
"""

import logging
import os
import time

import requests
from django.utils import timezone

from broadcasts.models import Broadcast, BroadcastRecipient
from broadcasts.services.audience import get_filtered_subscribers

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def send_broadcast(broadcast_id):
    """
    Send a broadcast to all matching subscribers.

    1. Verify status is DRAFT, transition to SENDING
    2. Build recipient list from audience filter
    3. Send individual emails via Brevo (or console in dev)
    4. Track per-recipient delivery status
    5. Transition to SENT when complete

    Returns the updated Broadcast instance.
    """
    broadcast = Broadcast.objects.get(pk=broadcast_id)

    if broadcast.status != Broadcast.Status.DRAFT:
        raise ValueError(
            "Broadcast %s is %s, not DRAFT — cannot send"
            % (broadcast_id, broadcast.status)
        )

    # Transition to SENDING
    broadcast.status = Broadcast.Status.SENDING
    broadcast.save(update_fields=["status", "updated_at"])
    logger.info("Broadcast %s: status set to SENDING", broadcast_id)

    api_key = os.environ.get("BREVO_API_KEY")
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")

    # Get filtered subscribers
    subscribers = get_filtered_subscribers(broadcast.audience_filter)

    # Create BroadcastRecipient rows
    recipients = []
    for subscriber in subscribers:
        recipient, _created = BroadcastRecipient.objects.get_or_create(
            broadcast=broadcast,
            subscriber=subscriber,
            defaults={"email": subscriber.email},
        )
        recipients.append(recipient)

    logger.info(
        "Broadcast %s: %d recipients created", broadcast_id, len(recipients)
    )

    # Send to each recipient
    sent_count = 0
    failed_count = 0

    for recipient in recipients:
        unsubscribe_url = (
            "%s/unsubscribe/%s/" % (frontend_url, recipient.subscriber.unsubscribe_token)
        )
        preferences_url = (
            "%s/preferences/%s/" % (frontend_url, recipient.subscriber.unsubscribe_token)
        )
        wrapped_html = _wrap_broadcast_html(
            broadcast.html_content, unsubscribe_url, preferences_url
        )

        if not api_key:
            # Dev mode: log to console, mark as SENT
            logger.info(
                "DEV MODE — Broadcast %s to %s: %s",
                broadcast_id,
                recipient.email,
                broadcast.subject,
            )
            recipient.status = BroadcastRecipient.DeliveryStatus.SENT
            recipient.sent_at = timezone.now()
            recipient.save(update_fields=["status", "sent_at"])
            sent_count += 1
        else:
            # Production: send via Brevo
            success = _send_single_email(
                api_key=api_key,
                to_email=recipient.email,
                to_name=recipient.subscriber.name,
                subject=broadcast.subject,
                html_content=wrapped_html,
                text_content=broadcast.text_content,
                recipient=recipient,
            )
            if success:
                sent_count += 1
            else:
                failed_count += 1

            # Rate limit: 0.5s between emails
            time.sleep(0.5)

    # Final status update
    broadcast.status = Broadcast.Status.SENT
    broadcast.sent_at = timezone.now()
    broadcast.recipient_count = len(recipients)
    broadcast.save(update_fields=["status", "sent_at", "recipient_count", "updated_at"])

    logger.info(
        "Broadcast %s: SENT — %d delivered, %d failed",
        broadcast_id,
        sent_count,
        failed_count,
    )

    return broadcast


def _send_single_email(api_key, to_email, to_name, subject, html_content,
                        text_content, recipient):
    """
    Send a single email via Brevo transactional API.

    Updates the BroadcastRecipient record with delivery status.
    Returns True if sent successfully, False otherwise.
    """
    payload = {
        "sender": {
            "name": "SJK(T) Connect",
            "email": "noreply@tamilschool.org",
        },
        "to": [{"email": to_email, "name": to_name}],
        "subject": subject,
        "htmlContent": html_content,
    }
    if text_content:
        payload["textContent"] = text_content

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

        recipient.status = BroadcastRecipient.DeliveryStatus.SENT
        recipient.sent_at = timezone.now()
        recipient.brevo_message_id = data.get("messageId", "")
        recipient.save(update_fields=["status", "sent_at", "brevo_message_id"])

        logger.info("Broadcast email sent to %s", to_email)
        return True

    except requests.RequestException as exc:
        recipient.status = BroadcastRecipient.DeliveryStatus.FAILED
        recipient.save(update_fields=["status"])
        logger.exception("Failed to send broadcast email to %s: %s", to_email, exc)
        return False


def _wrap_broadcast_html(html_content, unsubscribe_url, preferences_url):
    """
    Wrap broadcast HTML content in a standard email layout.

    Adds unsubscribe and preferences links in the footer.
    Uses HTML entities for special characters (not Unicode).
    """
    return """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f4f4f4;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background-color: #ffffff; border-radius: 8px; padding: 30px; margin-bottom: 20px;">
            %s
        </div>
        <div style="text-align: center; padding: 20px; color: #999; font-size: 12px;">
            <p>SJK(T) Connect &mdash; Tamil School Intelligence &amp; Advocacy Platform</p>
            <p>
                <a href="%s" style="color: #666; text-decoration: underline;">Manage Preferences</a>
                &nbsp;&middot;&nbsp;
                <a href="%s" style="color: #666; text-decoration: underline;">Unsubscribe</a>
            </p>
            <p>An initiative of the Malaysian Community Education Foundation (MCEF)</p>
        </div>
    </div>
</body>
</html>""" % (html_content, preferences_url, unsubscribe_url)
