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

# Owner decision 2026-06-11: news-type emails arrive from "SJK(T) News";
# everything else (monthly blast, parliament watch, transactional) keeps
# the platform name. Sender ADDRESS stays noreply@tamilschool.org so
# DKIM/DMARC are unaffected.
DEFAULT_SENDER_NAME = "SJK(T) Connect"
SENDER_NAMES_BY_KIND = {
    Broadcast.Kind.NEWS_DIGEST: "SJK(T) News",
    Broadcast.Kind.URGENT_ALERT: "SJK(T) News",
}


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

        allowance = _quota_allowance(broadcast, len(recipients), batch_size)
        if allowance > 0:
            sent_count, failed_count = _send_pending_recipients(
                broadcast, api_key, frontend_url, allowance
            )
        else:
            logger.warning(
                "Broadcast %s: Brevo daily quota exhausted — 0 of %d sent now; "
                "staying SENDING for the daily resume job to drain.",
                broadcast_id, len(recipients),
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
    except BrevoQuotaError:
        # Quota PROBE failed (network/auth) — transient, never terminal.
        # Stay SENDING so the daily resume_sending job retries tomorrow.
        # Marking this FAILED froze the digest anchor for 5 weeks
        # (2026-06-11 incident: broadcasts 79-82).
        logger.exception(
            "Broadcast %s: quota probe failed — staying SENDING for retry",
            broadcast_id,
        )
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

    sent_count = 0
    failed_count = 0

    try:
        allowance = _quota_allowance(broadcast, pending, batch_size)
        if allowance > 0:
            sent_count, failed_count = _send_pending_recipients(
                broadcast, api_key, frontend_url, allowance
            )
        else:
            logger.warning(
                "Broadcast %s: Brevo daily quota exhausted — %d still pending; "
                "staying SENDING for tomorrow's resume run.",
                broadcast_id, pending,
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
    except BrevoQuotaError:
        # Transient probe failure — stay SENDING, retry tomorrow. A quota
        # error is NOT terminal: this exact path marked broadcasts 79-82
        # FAILED and silently cut off half the subscriber list for 5 weeks
        # (2026-06-11 incident).
        logger.exception(
            "Broadcast %s: quota probe failed during resume — staying SENDING",
            broadcast_id,
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


def _quota_allowance(broadcast, recipient_count, batch_size):
    """How many emails may be sent right now under Brevo's daily cap.

    Returns ``min(planned, remaining)``. Running out of quota is
    TRANSIENT (tomorrow there is fresh quota), so this never raises on
    exhaustion — the caller sends what fits and leaves the broadcast in
    SENDING for the daily ``resume_sending`` job to drain over days.
    This replaces the old refuse-at-start gate, which raised, got caught
    as a generic failure, marked broadcasts FAILED, and froze the digest
    anchor for five weeks (2026-06-11 incident). It also un-breaks
    urgent alerts, whose ~335-recipient audience exceeds the 300/day cap
    and could otherwise never send at all.

    ``batch_size`` of 0 means "send everything". Raises
    ``BrevoQuotaError`` only when the quota PROBE fails — we refuse to
    send blind, but callers must treat that as transient too (stay
    SENDING, never FAILED).
    """
    quota = get_quota()

    planned = recipient_count
    if batch_size > 0:
        planned = min(planned, batch_size)

    if quota["dev_mode"]:
        return planned

    allowance = min(planned, quota["remaining"])
    if allowance < planned:
        logger.warning(
            "Broadcast %d: planned %d sends but Brevo has %d remaining today "
            "(quota=%d, used=%d) — sending %d now, the rest stays PENDING "
            "for the daily resume job.",
            broadcast.pk,
            planned,
            quota["remaining"],
            quota["daily_quota"],
            quota["used_today"],
            allowance,
        )
    return allowance


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
    sender_name = SENDER_NAMES_BY_KIND.get(broadcast.kind, DEFAULT_SENDER_NAME)

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
                sender_name=sender_name,
            )
            if success:
                sent_count += 1
            else:
                failed_count += 1
            time.sleep(0.5)

    return sent_count, failed_count


def _send_single_email(api_key, to_email, to_name, subject, html_content,
                        text_content, recipient,
                        sender_name=DEFAULT_SENDER_NAME):
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
            "name": sender_name,
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


def send_test(broadcast_id, recipient_emails):
    """Send a broadcast to arbitrary test addresses without touching its state.

    Sprint 25: lets an admin verify a DRAFT broadcast on their own inbox
    before releasing it to ~519 real subscribers. Test sends DO NOT:
      - change `broadcast.status` (it stays DRAFT)
      - create `BroadcastRecipient` rows (the recipients list / counts
        remain the audit trail for the eventual real send)
      - apply the Brevo daily-quota gate (test sends are bounded and a
        300/day cap shouldn't block a 2-email sanity check)

    Per-email Brevo rate limit (0.5s) is honoured.

    Returns ``(sent_count, failed_count)``.
    """
    broadcast = Broadcast.objects.get(pk=broadcast_id)
    api_key = os.environ.get("BREVO_API_KEY")
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    sender_name = SENDER_NAMES_BY_KIND.get(broadcast.kind, DEFAULT_SENDER_NAME)

    # The footer's unsub/prefs links need a real token; a test-only stub
    # token keeps the rendered HTML structurally identical to a real send
    # while making it obvious in the inbox that this is a test.
    test_token = "TEST-SEND-DO-NOT-CLICK"
    unsubscribe_url = f"{frontend_url}/unsubscribe/{test_token}/"
    preferences_url = f"{frontend_url}/preferences/{test_token}/"
    wrapped_html = _wrap_broadcast_html(
        broadcast.html_content, unsubscribe_url, preferences_url
    )
    test_subject = f"[TEST] {broadcast.subject}"

    sent_count = 0
    failed_count = 0
    for email in recipient_emails:
        email = email.strip()
        if not email:
            continue
        if not api_key:
            logger.info(
                "DEV MODE — Broadcast %s test-send to %s: %s",
                broadcast.pk, email, test_subject,
            )
            sent_count += 1
            continue
        try:
            response = requests.post(
                BREVO_API_URL,
                json={
                    "sender": {
                        "name": sender_name,
                        "email": "noreply@tamilschool.org",
                    },
                    "replyTo": {
                        "email": "feedback@tamilschool.org",
                        "name": "SJK(T) Connect",
                    },
                    "to": [{"email": email}],
                    "subject": test_subject,
                    "htmlContent": wrapped_html,
                    "textContent": broadcast.text_content,
                },
                headers={
                    "api-key": api_key,
                    "Content-Type": "application/json",
                },
                timeout=10,
            )
            response.raise_for_status()
            sent_count += 1
            logger.info("Test send to %s for broadcast %s succeeded", email, broadcast.pk)
        except requests.RequestException as exc:
            failed_count += 1
            logger.exception(
                "Test send to %s for broadcast %s failed: %s",
                email, broadcast.pk, exc,
            )
        time.sleep(0.5)

    return sent_count, failed_count


# Sprint 24 task #7 — every broadcast (monthly blast, news digest, urgent
# alert, parliament watch) gets these in the footer. Forward = mailto:
# with a prefilled subject so a one-tap share works in any mail client.
DEFAULT_DONATE_URL = "https://tamilschool.org/donate"
DEFAULT_FORWARD_URL = (
    "mailto:?subject=Tamil%20Schools%20News%20Blast"
    "&body=Have%20a%20look%20at%20this%20news%20blast"
    "%20from%20tamilschool.org%0A%0A"
    "Open%20the%20latest%20blast%3A%20"
    "https%3A%2F%2Ftamilschool.org%2Fen%2Fnews"
)
# NOTE (2026-07-05, owner ask): the request was "attach the newsletter"
# so the recipient forwards the actual email. RFC 6068 mailto: does NOT
# support attachments -- browsers/mail clients drop any `attachment=`
# param. The pragmatic substitute: link back to the live news page in
# the mailto body so the recipient can open + share the stories. A
# proper "View this email in your browser" pattern needs a public
# broadcast-view URL (backlog item).


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
    <meta name="x-apple-disable-message-reformatting">
    <meta name="color-scheme" content="light">
    <meta name="supported-color-schemes" content="light">
</head>
<body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f4f4f4; word-break: break-word;">
    <!-- Mobile-fix 2026-07-04: outer padding trimmed from 20px to 10px so a
         320px viewport leaves room for the inner card, and the inner card
         padding cut from 30px to 20px so text isn't crammed against edges. -->
    <div style="max-width: 600px; margin: 0 auto; padding: 10px;">
        <div style="background-color: #ffffff; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
            {content}
        </div>
        <!-- 2026-07-05: footer inverted to navy panel to match the Take
             Action anchor above, giving the email a solid navy close. -->
        <div style="background: #1e3a8a; border-radius: 8px; text-align: center; padding: 24px 20px; color: #bfdbfe; font-size: 12px; line-height: 1.6;">
            <p style="margin: 0 0 12px 0; color: #ffffff; font-weight: 600;">SJK(T) Connect &mdash; Tamil School Intelligence &amp; Advocacy Platform</p>
            <p style="margin: 12px 0;">
                <a href="{donate}" style="color: #ffffff; text-decoration: none; font-weight: 600;">Donate to Tamil Foundation</a>
                &nbsp;&middot;&nbsp;
                <a href="{forward}" style="color: #ffffff; text-decoration: none; font-weight: 600;">Forward to a friend</a>
            </p>
            <p style="margin: 12px 0;">
                <a href="{prefs}" style="color: #bfdbfe; text-decoration: underline;">Manage Preferences</a>
                &nbsp;&middot;&nbsp;
                <a href="{unsub}" style="color: #bfdbfe; text-decoration: underline;">Unsubscribe</a>
            </p>
            <p style="margin: 12px 0 0 0; color: #93c5fd;">An initiative of Malaysian Tamil Educational Research &amp; Development Foundation (Tamil Foundation)</p>
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
