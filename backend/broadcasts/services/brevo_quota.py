"""
Pre-flight Brevo daily-quota check.

Free-tier Brevo accounts cap outbound transactional sends at 300/day.
At 519 active subscribers, a single MONTHLY_BLAST run exceeds the cap
and the tail end of the send gets 400s from Brevo. The April 2026 blast
hit this at recipient 514/519.

This module exists so send_broadcast() and the compose commands can ask
"will this send fit in today's remaining quota?" before queuing anything.
Counting via our own BroadcastRecipient.sent_at gives a more accurate
used_today figure than parsing Brevo's plan structure (which doesn't
always surface the daily counter for free-tier plans).
"""

import logging
import os

import requests
from django.utils import timezone

logger = logging.getLogger(__name__)

BREVO_ACCOUNT_URL = "https://api.brevo.com/v3/account"
DEFAULT_DAILY_QUOTA = 300


class BrevoQuotaError(Exception):
    """Raised when the Brevo /v3/account probe fails."""


def get_quota() -> dict:
    """Return today's Brevo send budget.

    Shape: ``{daily_quota: int, used_today: int, remaining: int,
    dev_mode: bool}``.

    ``daily_quota`` defaults to 300 (free-tier) and can be overridden
    via the ``BREVO_DAILY_QUOTA`` env var.

    ``used_today`` counts our own ``BroadcastRecipient`` rows with
    ``sent_at`` in the current calendar day (timezone-aware) and a
    status that means a Brevo send was attempted (SENT, DELIVERED,
    BOUNCED, SPAM). FAILED rows are excluded because they typically
    represent network errors that never reached Brevo's quota counter.

    When ``BREVO_API_KEY`` is unset (dev mode), returns the full quota
    with ``dev_mode=True`` and skips the API probe. Callers can treat
    this as "no cap" or as "you're not really sending anywhere".

    Raises ``BrevoQuotaError`` if the Brevo probe fails — we'd rather
    refuse to send than send blind.
    """
    daily_quota = int(os.environ.get("BREVO_DAILY_QUOTA", DEFAULT_DAILY_QUOTA))
    api_key = os.environ.get("BREVO_API_KEY")

    if not api_key:
        return {
            "daily_quota": daily_quota,
            "used_today": 0,
            "remaining": daily_quota,
            "dev_mode": True,
        }

    try:
        response = requests.get(
            BREVO_ACCOUNT_URL,
            headers={"api-key": api_key, "Accept": "application/json"},
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise BrevoQuotaError(f"Brevo /v3/account probe failed: {exc}") from exc

    used_today = _count_sent_today()
    remaining = max(0, daily_quota - used_today)

    logger.info(
        "Brevo quota: %d/%d used today, %d remaining",
        used_today, daily_quota, remaining,
    )

    return {
        "daily_quota": daily_quota,
        "used_today": used_today,
        "remaining": remaining,
        "dev_mode": False,
    }


def _count_sent_today() -> int:
    """Count BroadcastRecipient rows sent so far today.

    Uses the project's active timezone (MYT) for day boundaries. Brevo
    counts in UTC, so there's a ~8h skew at midnight MYT — small enough
    to swallow given the 300/day cap leaves plenty of headroom.
    """
    # Local import avoids circular import at module load time
    # (broadcasts.models imports from this module's parent package).
    from broadcasts.models import BroadcastRecipient

    now = timezone.now()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return BroadcastRecipient.objects.filter(
        sent_at__gte=day_start,
        status__in=[
            BroadcastRecipient.DeliveryStatus.SENT,
            BroadcastRecipient.DeliveryStatus.DELIVERED,
            BroadcastRecipient.DeliveryStatus.BOUNCED,
            BroadcastRecipient.DeliveryStatus.SPAM,
        ],
    ).count()
