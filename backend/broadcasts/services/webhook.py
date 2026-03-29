"""
Service for processing Brevo webhook events.

Brevo sends POST requests with delivery events (delivered, opened, clicked,
hard_bounce, soft_bounce, spam, unsubscribed). We match by message-id to
BroadcastRecipient.brevo_message_id and update engagement tracking fields.

Hard bounces increment Subscriber.bounce_count; at 3 the subscriber is
auto-deactivated.
"""

import logging

from django.db.models import F
from django.utils import timezone

from broadcasts.models import BroadcastRecipient
from subscribers.models import Subscriber

logger = logging.getLogger(__name__)

HARD_BOUNCE_THRESHOLD = 1


def process_brevo_event(event: dict) -> bool:
    """
    Process a single Brevo webhook event payload.

    Returns True if the event was processed, False if skipped.
    """
    event_type = event.get("event")
    message_id = event.get("message-id") or event.get("message_id", "")

    if not event_type or not message_id:
        logger.warning("Brevo webhook: missing event or message-id: %s", event)
        return False

    # Strip angle brackets if present (Brevo sometimes wraps in < >)
    message_id = message_id.strip("<>")

    # Match with or without angle brackets (sender stores with <>, webhook sends without)
    recipient = (
        BroadcastRecipient.objects
        .select_related("subscriber")
        .filter(brevo_message_id__in=[message_id, f"<{message_id}>"])
        .first()
    )

    if not recipient:
        logger.debug("Brevo webhook: no recipient for message-id %s", message_id)
        return False

    now = timezone.now()

    if event_type == "delivered":
        recipient.status = BroadcastRecipient.DeliveryStatus.DELIVERED
        recipient.delivered_at = now
        recipient.save(update_fields=["status", "delivered_at"])
        logger.info("Delivered: %s (message %s)", recipient.email, message_id)

    elif event_type == "opened" or event_type == "unique_opened":
        recipient.open_count = F("open_count") + 1
        if not recipient.opened_at:
            recipient.opened_at = now
        # Upgrade status to DELIVERED if still SENT
        if recipient.status == BroadcastRecipient.DeliveryStatus.SENT:
            recipient.status = BroadcastRecipient.DeliveryStatus.DELIVERED
            recipient.delivered_at = recipient.delivered_at or now
            recipient.save(update_fields=[
                "open_count", "opened_at", "status", "delivered_at",
            ])
        else:
            recipient.save(update_fields=["open_count", "opened_at"])
        logger.info("Opened: %s (message %s)", recipient.email, message_id)

    elif event_type in ("click", "clicked"):
        recipient.click_count = F("click_count") + 1
        if not recipient.clicked_at:
            recipient.clicked_at = now
        # Upgrade status to DELIVERED if still SENT
        if recipient.status == BroadcastRecipient.DeliveryStatus.SENT:
            recipient.status = BroadcastRecipient.DeliveryStatus.DELIVERED
            recipient.delivered_at = recipient.delivered_at or now
            recipient.save(update_fields=[
                "click_count", "clicked_at", "status", "delivered_at",
            ])
        else:
            recipient.save(update_fields=["click_count", "clicked_at"])
        logger.info("Clicked: %s (message %s)", recipient.email, message_id)

    elif event_type in ("hard_bounce", "hard_bounced"):
        recipient.status = BroadcastRecipient.DeliveryStatus.BOUNCED
        recipient.bounce_type = BroadcastRecipient.BounceType.HARD
        recipient.save(update_fields=["status", "bounce_type"])
        _increment_bounce_count(recipient.subscriber)
        logger.warning("Hard bounce: %s (message %s)", recipient.email, message_id)

    elif event_type in ("soft_bounce", "soft_bounced"):
        recipient.status = BroadcastRecipient.DeliveryStatus.BOUNCED
        recipient.bounce_type = BroadcastRecipient.BounceType.SOFT
        recipient.save(update_fields=["status", "bounce_type"])
        logger.info("Soft bounce: %s (message %s)", recipient.email, message_id)

    elif event_type in ("spam", "complaint"):
        recipient.status = BroadcastRecipient.DeliveryStatus.SPAM
        recipient.save(update_fields=["status"])
        logger.warning("Spam complaint: %s (message %s)", recipient.email, message_id)

    elif event_type == "unsubscribed":
        # Brevo-side unsubscribe — deactivate our subscriber too
        subscriber = recipient.subscriber
        if subscriber.is_active:
            subscriber.is_active = False
            subscriber.unsubscribed_at = now
            subscriber.save(update_fields=["is_active", "unsubscribed_at", "updated_at"])
            logger.info("Unsubscribed via Brevo: %s", recipient.email)

    else:
        logger.debug("Brevo webhook: unhandled event type %s", event_type)
        return False

    return True


def _increment_bounce_count(subscriber: Subscriber) -> None:
    """Increment bounce count and auto-deactivate at threshold."""
    Subscriber.objects.filter(pk=subscriber.pk).update(
        bounce_count=F("bounce_count") + 1
    )
    subscriber.refresh_from_db()

    if subscriber.bounce_count >= HARD_BOUNCE_THRESHOLD:
        subscriber.is_active = False
        subscriber.save(update_fields=["is_active", "updated_at"])
        logger.warning(
            "Auto-deactivated subscriber %s after %d hard bounces",
            subscriber.email,
            subscriber.bounce_count,
        )
