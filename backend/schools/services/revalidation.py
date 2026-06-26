"""Server-driven ISR revalidation for the Next.js frontend.

TD-21 (audit 2026-06-26): the previous design had the browser POST to
`/api/revalidate` after a successful school edit. That endpoint was
unauthenticated — a scripted attacker could trigger 60 ISR
regenerations per second (3 locales × 2 URLs per school × N req/s),
each one running the full SchoolDetailPage component + Django API +
Supabase fetch. With two prior egress incidents (Sprint 17, Sprint
21) in the history, an unauthenticated scriptable amplifier was
exactly the vector that recreated them.

The fix: trigger revalidation from the BACKEND after `serializer.save()`
in the edit views. The frontend route handler now requires an
`X-Revalidate-Token` header, validated against `REVALIDATE_TOKEN` env
var. The browser no longer calls revalidate directly. Net effect:
- Same correctness (page busts after every save).
- No abuse vector (token is server-side only, never bundled).
- Removes the "stale browser fails to revalidate" failure mode.

Env vars (set on Cloud Run for both api + web):
- `REVALIDATE_WEBHOOK_URL`: e.g. `https://tamilschool.org/api/revalidate`
- `REVALIDATE_TOKEN`: any opaque secret string; must match between
  api (sender) and web (verifier).

If either env var is unset, this module logs and no-ops — safe for
local dev and for any environment that doesn't want server-driven
revalidation (the ISR cache will simply expire naturally in 24h).
"""

import logging
import os
import re
from typing import Optional

import requests

logger = logging.getLogger(__name__)


_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_SJKT_PREFIX_RE = re.compile(r"^sjk\s*\(t\)\s*|^sjkt\s+", re.IGNORECASE)


def _slugify_part(text: str) -> str:
    """Mirror of `frontend/lib/urls.ts::slugifyPart` for slug parity.

    Lowercases, strips the SJK(T) / SJKT prefix, replaces non-alnum
    runs with hyphens, trims leading/trailing hyphens.
    """
    if not text:
        return ""
    out = text.lower()
    out = _SJKT_PREFIX_RE.sub("", out)
    out = _NON_ALNUM_RE.sub("-", out)
    return out.strip("-")


def build_school_slug(moe_code: str, short_name: Optional[str], city: Optional[str]) -> str:
    """Build the canonical slug for a school. Mirrors `schoolPath()` in
    `frontend/lib/urls.ts`. Returns the slug WITHOUT the leading
    `/school/` prefix — the route handler adds the locale + prefix.
    """
    parts = [_slugify_part(short_name or ""), _slugify_part(city or ""), moe_code.lower()]
    return "-".join(p for p in parts if p)


def trigger_school_revalidate(school) -> None:
    """Fire-and-forget POST to the Next.js revalidate route for a school.

    Swallows all exceptions — revalidation failure must not block the
    edit's HTTP 200 response. Worst case is the natural 24h ISR expiry.
    """
    url = os.environ.get("REVALIDATE_WEBHOOK_URL", "").strip()
    token = os.environ.get("REVALIDATE_TOKEN", "").strip()
    if not url or not token:
        logger.debug(
            "ISR revalidation skipped (REVALIDATE_WEBHOOK_URL or "
            "REVALIDATE_TOKEN unset)."
        )
        return

    slug = build_school_slug(school.moe_code, school.short_name, school.city)
    payload = {
        "type": "school",
        "key": school.moe_code,
        "slug": slug,
    }

    try:
        resp = requests.post(
            url,
            json=payload,
            headers={"X-Revalidate-Token": token, "Content-Type": "application/json"},
            timeout=5,
        )
        if resp.status_code >= 400:
            logger.warning(
                "ISR revalidation returned %s for %s: %s",
                resp.status_code, school.moe_code, resp.text[:200],
            )
        else:
            logger.info("ISR revalidated for %s", school.moe_code)
    except Exception as exc:
        # Network failures, DNS, timeout, etc. — all non-fatal.
        logger.warning("ISR revalidation failed for %s: %s", school.moe_code, exc)
