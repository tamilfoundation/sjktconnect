import logging

from django.db import transaction
from django.utils import timezone

from subscribers.models import Subscriber, SubscriptionPreference

logger = logging.getLogger(__name__)


def subscribe(email, name="", organisation=""):
    """
    Create or reactivate a subscriber with all preferences enabled.

    Returns (subscriber, created) tuple. If the subscriber already exists
    and is active, returns (subscriber, False) — idempotent.
    If previously unsubscribed, reactivates them.
    """
    email = email.lower().strip()

    with transaction.atomic():
        subscriber, created = Subscriber.objects.get_or_create(
            email=email,
            defaults={"name": name, "organisation": organisation},
        )

        if created:
            _create_default_preferences(subscriber)
            logger.info("New subscriber: %s", email)
            return subscriber, True

        # Existing subscriber — reactivate if previously unsubscribed
        if not subscriber.is_active:
            subscriber.is_active = True
            subscriber.unsubscribed_at = None
            subscriber.save(update_fields=["is_active", "unsubscribed_at", "updated_at"])
            _ensure_preferences_exist(subscriber)
            logger.info("Reactivated subscriber: %s", email)
            return subscriber, True

        # Already active — update name/org if provided
        updated = False
        if name and not subscriber.name:
            subscriber.name = name
            updated = True
        if organisation and not subscriber.organisation:
            subscriber.organisation = organisation
            updated = True
        if updated:
            subscriber.save(update_fields=["name", "organisation", "updated_at"])

        return subscriber, False


def unsubscribe(token):
    """
    Deactivate a subscriber by their unsubscribe token.

    Returns the subscriber if found and deactivated, None if token invalid.
    """
    try:
        subscriber = Subscriber.objects.get(unsubscribe_token=token)
    except Subscriber.DoesNotExist:
        return None

    if not subscriber.is_active:
        return subscriber  # Already unsubscribed, idempotent

    subscriber.is_active = False
    subscriber.unsubscribed_at = timezone.now()
    subscriber.save(update_fields=["is_active", "unsubscribed_at", "updated_at"])
    logger.info("Unsubscribed: %s", subscriber.email)
    return subscriber


def get_preferences(token):
    """
    Get a subscriber's preferences by their unsubscribe token.

    Returns (subscriber, preferences) or (None, None) if token invalid.
    """
    try:
        subscriber = Subscriber.objects.get(unsubscribe_token=token)
    except Subscriber.DoesNotExist:
        return None, None

    _ensure_preferences_exist(subscriber)
    preferences = subscriber.preferences.all()
    return subscriber, preferences


def update_preferences(token, preference_updates):
    """
    Update a subscriber's category preferences.

    preference_updates: dict of {category: is_enabled} e.g.
    {"PARLIAMENT_WATCH": True, "NEWS_WATCH": False}

    Returns (subscriber, preferences) or (None, None) if token invalid.
    """
    try:
        subscriber = Subscriber.objects.get(unsubscribe_token=token)
    except Subscriber.DoesNotExist:
        return None, None

    _ensure_preferences_exist(subscriber)

    valid_categories = dict(SubscriptionPreference.CATEGORY_CHOICES)
    for category, is_enabled in preference_updates.items():
        if category in valid_categories:
            subscriber.preferences.filter(category=category).update(
                is_enabled=is_enabled
            )

    preferences = subscriber.preferences.all()
    return subscriber, preferences


def _create_default_preferences(subscriber):
    """Create all category preferences enabled by default."""
    for category, _ in SubscriptionPreference.CATEGORY_CHOICES:
        SubscriptionPreference.objects.create(
            subscriber=subscriber,
            category=category,
            is_enabled=True,
        )


def _ensure_preferences_exist(subscriber):
    """Ensure all categories have a preference row (for reactivated subscribers)."""
    existing = set(subscriber.preferences.values_list("category", flat=True))
    for category, _ in SubscriptionPreference.CATEGORY_CHOICES:
        if category not in existing:
            SubscriptionPreference.objects.create(
                subscriber=subscriber,
                category=category,
                is_enabled=True,
            )
