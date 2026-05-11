"""
Service for sending broadcast emails via Brevo transactional API.

Handles status transitions (DRAFT -> SENDING -> SENT), per-recipient
tracking, rate limiting, and dev-mode console fallback.
"""

import logging
import os
import time

import requests
from django.db import transaction
from django.utils import timezone

from broadcasts.models import Broadcast, BroadcastRecipient
from broadcasts.services.audience import get_filtered_subscribers
from broadcasts.services.brevo_quota import BrevoQuotaError, get_quota

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


class QuotaExceededError(Exception):
    """Raised when a planned send exceeds today's Brevo quota."""


def send_broadcast(broadcast_id, batch_size=0):
    """
    Send a broadcast to matching subscribers.

    If batch_size > 0, sends at most batch_size emails per call and leaves
    the broadcast in SENDING status until all recipients are done. Call
    resume_broadcast() to continue sending in subsequent runs.

    1. Verify status is DRAFT, transition to SENDING
    2. Build recipient list from audience filter
    3. Send individual emails via Brevo (or console in dev)
    4. Track per-recipient delivery status
    5. Transition to SENT when all recipients are processed

    Returns the updated Broadcast instance.
    """
    # C1 fix: atomic conditional update prevents race condition
    with transaction.atomic():
        updated = Broadcast.objects.filter(
            pk=broadcast_id, status=Broadcast.Status.DRAFT
        ).update(status=Broadcast.Status.SENDING)
        if not updated:
            broadcast = Broadcast.objects.get(pk=broadcast_id)
            raise ValueError(
                "Broadcast %s is %s, not DRAFT — cannot send"
                % (broadcast_id, broadcast.status)
            )
        broadcast = Broadcast.objects.get(pk=broadcast_id)
    logger.info("Broadcast %s: status set to SENDING", broadcast_id)

    api_key = os.environ.get("BREVO_API_KEY")
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")

    # C2 fix: wrap entire send process so broadcast transitions to FAILED on exception
    sent_count = 0
    failed_count = 0
    recipients = []

    try:
        # Get filtered subscribers
        subscribers = get_filtered_subscribers(broadcast.audience_filter)

        # Create BroadcastRecipient rows
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

        _enforce_quota(broadcast, recipients, batch_size)

        sent_count, failed_count = _send_pending_recipients(
            broadcast, api_key, frontend_url, batch_size
        )

        # Check if there are still PENDING recipients
        pending = broadcast.recipients.filter(
            status=BroadcastRecipient.DeliveryStatus.PENDING
        ).count()
        if pending > 0:
            # More to send — stay in SENDING status
            logger.info(
                "Broadcast %s: batch complete, %d still pending",
                broadcast_id, pending,
            )
        else:
            broadcast.status = Broadcast.Status.SENT
    except Exception:
        broadcast.status = Broadcast.Status.FAILED
        logger.exception("Broadcast %s failed during send", broadcast_id)
    finally:
        broadcast.sent_at = timezone.now()
        broadcast.recipient_count = len(recipients)
        broadcast.save(update_fields=["status", "sent_at", "recipient_count", "updated_at"])

    logger.info(
        "Broadcast %s: %s — %d delivered, %d failed",
        broadcast_id,
        broadcast.status,
        sent_count,
        failed_count,
    )

    return broadcast


def resume_broadcast(broadcast_id, batch_size=250):
    """
    Resume sending a broadcast that is in SENDING status.

    Picks up PENDING recipients and sends the next batch_size emails.
    Transitions to SENT when no PENDING recipients remain.

    Returns the updated Broadcast instance, or None if nothing to resume.
    """
    broadcast = Broadcast.objects.filter(
        pk=broadcast_id, status=Broadcast.Status.SENDING
    ).first()
    if not broadcast:
        logger.info("Broadcast %s: not in SENDING status, skipping", broadcast_id)
        return None

    pending = broadcast.recipients.filter(
        status=BroadcastRecipient.DeliveryStatus.PENDING
    ).count()
    if pending == 0:
        broadcast.status = Broadcast.Status.SENT
        broadcast.save(update_fields=["status", "updated_at"])
        logger.info("Broadcast %s: no pending recipients, marked SENT", broadcast_id)
        return broadcast

    api_key = os.environ.get("BREVO_API_KEY")
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")

    try:
        pending_recipients = list(
            broadcast.recipients.filter(
                status=BroadcastRecipient.DeliveryStatus.PENDING
            )
        )
        _enforce_quota(broadcast, pending_recipients, batch_size)

        sent_count, failed_count = _send_pending_recipients(
            broadcast, api_key, frontend_url, batch_size
        )

        remaining = broadcast.recipients.filter(
            status=BroadcastRecipient.DeliveryStatus.PENDING
        ).count()
        if remaining == 0:
            broadcast.status = Broadcast.Status.SENT
            broadcast.sent_at = timezone.now()
            broadcast.save(update_fields=["status", "sent_at", "updated_at"])
        else:
            logger.info(
                "Broadcast %s: batch done, %d still pending",
                broadcast_id, remaining,
            )
    except Exception:
        broadcast.status = Broadcast.Status.FAILED
        broadcast.save(update_fields=["status", "updated_at"])
        logger.exception("Broadcast %s failed during resume", broadcast_id)

    logger.info(
        "Broadcast %s: %s — %d sent, %d failed this batch",
        broadcast_id, broadcast.status, sent_count, failed_count,
    )
    return broadcast


def _enforce_quota(broadcast, recipients, batch_size):
    """Pre-flight Brevo quota check; raise if planned send exceeds remaining.

    The April 2026 blast hit Brevo's 300/day cap at 514/519 and the
    tail-end 400s were swallowed silently. With this gate, the send
    aborts with the three numbers visible in the log instead.

    ``batch_size`` of 0 means "send everything"; bounds the planned
    count to ``len(recipients)``. A positive ``batch_size`` caps the
    planned count to that batch.
    """
    try:
        quota = get_quota()
    except BrevoQuotaError as exc:
        # Quota probe failed (network, auth) — refuse to send blind.
        logger.error("Broadcast %s: quota probe failed: %s", broadcast.pk, exc)
        raise

    if quota["dev_mode"]:
        return

    planned = len(recipients)
    if batch_size > 0:
        planned = min(planned, batch_size)

    if planned > quota["remaining"]:
        raise QuotaExceededError(
            "Broadcast %d planned %d sends but Brevo has %d remaining today "
            "(quota=%d, used=%d). Wait until tomorrow or pass batch_size <= %d."
            % (
                broadcast.pk,
                planned,
                quota["remaining"],
                quota["daily_quota"],
                quota["used_today"],
                quota["remaining"],
            )
        )


def _send_pending_recipients(broadcast, api_key, frontend_url, batch_size=0):
    """
    Send emails to PENDING recipients of a broadcast.

    If batch_size > 0, sends at most batch_size emails.
    Returns (sent_count, failed_count).
    """
    recipients = list(
        broadcast.recipients.filter(
            status=BroadcastRecipient.DeliveryStatus.PENDING
        ).select_related("subscriber")
        .order_by("subscriber__created_at")
    )
    if batch_size > 0:
        recipients = recipients[:batch_size]

    sent_count = 0
    failed_count = 0

    for recipient in recipients:
        unsubscribe_url = (
            "{}/unsubscribe/{}/".format(frontend_url, recipient.subscriber.unsubscribe_token)
        )
        preferences_url = (
            "{}/preferences/{}/".format(frontend_url, recipient.subscriber.unsubscribe_token)
        )
        wrapped_html = _wrap_broadcast_html(
            broadcast.html_content, unsubscribe_url, preferences_url
        )

        if not api_key:
            logger.info(
                "DEV MODE — Broadcast %s to %s: %s",
                broadcast.pk, recipient.email, broadcast.subject,
            )
            recipient.status = BroadcastRecipient.DeliveryStatus.SENT
            recipient.sent_at = timezone.now()
            recipient.save(update_fields=["status", "sent_at"])
            sent_count += 1
        else:
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
            time.sleep(0.5)

    return sent_count, failed_count


def _send_single_email(api_key, to_email, to_name, subject, html_content,
                        text_content, recipient):
    """
    Send a single email via Brevo transactional API.

    Updates the BroadcastRecipient record with delivery status.
    Returns True if sent successfully, False otherwise.
    """
    # Brevo returns 400 if "name" is present but empty, so omit it
    # entirely when the subscriber has no display name (default for
    # bulk-imported addresses without a paired name field).
    to_entry: dict = {"email": to_email}
    if to_name:
        to_entry["name"] = to_name

    payload = {
        "sender": {
            "name": "SJK(T) Connect",
            "email": "noreply@tamilschool.org",
        },
        "replyTo": {
            "email": "feedback@tamilschool.org",
            "name": "SJK(T) Connect",
        },
        "to": [to_entry],
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
        recipient.brevo_message_id = data.get("messageId", "").strip("<>")
        recipient.save(update_fields=["status", "sent_at", "brevo_message_id"])

        logger.info("Broadcast email sent to %s", to_email)
        return True

    except requests.RequestException as exc:
        recipient.status = BroadcastRecipient.DeliveryStatus.FAILED
        recipient.save(update_fields=["status"])
        logger.exception("Failed to send broadcast email to %s: %s", to_email, exc)
        return False


# Sprint 24 task #7 — every broadcast (monthly blast, news digest, urgent
# alert, parliament watch) gets these in the footer. Forward = mailto:
# with a prefilled subject so a one-tap share works in any mail client.
DEFAULT_DONATE_URL = "https://tamilschool.org/donate"
DEFAULT_FORWARD_URL = (
    "mailto:?subject=Tamil%20Schools%20Intelligence%20Blast"
    "&body=Have%20a%20look%20at%20this%20month%27s%20digest"
    "%20from%20tamilschool.org"
)


def _wrap_broadcast_html(
    html_content,
    unsubscribe_url,
    preferences_url,
    donate_url=DEFAULT_DONATE_URL,
    forward_url=DEFAULT_FORWARD_URL,
):
    """
    Wrap broadcast HTML content in a standard email layout.

    Footer layout (Sprint 24 task #7):
      Row 1: Donate &middot; Forward to a friend  (calls to action)
      Row 2: Manage Preferences &middot; Unsubscribe  (compliance)
      Row 3: An initiative of ...

    Pulling Donate + Forward up into the global wrap means news digests,
    urgent alerts, and Parliament Watch broadcasts ALL get the same two
    CTAs without each template having to embed them. Body-level CTAs in
    the monthly blast (Take Action section) are independent and stay.

    Uses HTML entities for special characters (not Unicode) per lesson 21.
    """
    # M2 fix: use .format() instead of % to avoid breakage on literal % in content
    return """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f4f4f4;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background-color: #ffffff; border-radius: 8px; padding: 30px; margin-bottom: 20px;">
            {content}
        </div>
        <div style="text-align: center; padding: 20px; color: #999; font-size: 12px;">
            <p>SJK(T) Connect &mdash; Tamil School Intelligence &amp; Advocacy Platform</p>
            <p style="margin: 12px 0;">
                <a href="{donate}" style="color: #7c3aed; text-decoration: none; font-weight: 600;">Donate to Tamil Foundation</a>
                &nbsp;&middot;&nbsp;
                <a href="{forward}" style="color: #7c3aed; text-decoration: none; font-weight: 600;">Forward to a friend</a>
            </p>
            <p>
                <a href="{prefs}" style="color: #666; text-decoration: underline;">Manage Preferences</a>
                &nbsp;&middot;&nbsp;
                <a href="{unsub}" style="color: #666; text-decoration: underline;">Unsubscribe</a>
            </p>
            <p>An initiative of Malaysian Tamil Educational Research &amp; Development Foundation (Tamil Foundation)</p>
        </div>
    </div>
</body>
</html>""".format(
        content=html_content,
        prefs=preferences_url,
        unsub=unsubscribe_url,
        donate=donate_url,
        forward=forward_url,
    )
