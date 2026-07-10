"""ISR cache invalidation for Parliament Watch pages after a brief publishes.

Mirrors ``schools.services.revalidation`` (school edits) — that loop existed;
sitting briefs had no equivalent, so a newly-published brief sat invisible on
the cached `/parliament-watch` home and `/parliament-watch/sittings` list for
up to 24h (their ISR `revalidate = 86400`). This closes that gap: publishing a
brief now refreshes both list pages plus the brief's own detail page.
"""

import logging
import os

import requests

logger = logging.getLogger(__name__)


def trigger_brief_revalidate(brief) -> None:
    """Fire-and-forget POST to the Next.js revalidate route for a brief.

    Swallows all exceptions — revalidation failure must not block the
    publish response. Worst case is the natural 24h ISR expiry.
    """
    url = os.environ.get("REVALIDATE_WEBHOOK_URL", "").strip()
    token = os.environ.get("REVALIDATE_TOKEN", "").strip()
    if not url or not token:
        logger.debug(
            "Parliament ISR revalidation skipped (REVALIDATE_WEBHOOK_URL or "
            "REVALIDATE_TOKEN unset)."
        )
        return

    payload = {"type": "parliament", "key": str(brief.id)}

    try:
        resp = requests.post(
            url,
            json=payload,
            headers={"X-Revalidate-Token": token, "Content-Type": "application/json"},
            timeout=5,
        )
        if resp.status_code >= 400:
            logger.warning(
                "Parliament ISR revalidation returned %s for brief %s: %s",
                resp.status_code, brief.id, resp.text[:200],
            )
        else:
            logger.info("Parliament ISR revalidated for brief %s", brief.id)
    except Exception as exc:
        logger.warning("Parliament ISR revalidation failed for brief %s: %s", brief.id, exc)
