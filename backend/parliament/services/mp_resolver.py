"""Cross-reference Gemini-extracted MP data against the MP database.

Looks up the MP by constituency (name or code) or by name substring.
Enriches missing fields (party, constituency) from the database.
"""

import logging

from django.db.models import Q

from parliament.models import MP

logger = logging.getLogger(__name__)


def resolve_mp(mp_name: str, mp_constituency: str, mp_party: str) -> dict:
    """Try to match extracted MP data against the MP database.

    Matching priority:
    1. Constituency code (exact, e.g. "P078")
    2. Constituency name (case-insensitive, e.g. "Klang")
    3. MP name substring (case-insensitive)

    Returns dict with mp_name, mp_constituency, mp_party — enriched
    from DB where possible, original values preserved otherwise.
    """
    result = {
        "mp_name": mp_name,
        "mp_constituency": mp_constituency,
        "mp_party": mp_party,
    }

    mp = None

    # Try constituency match first (most reliable)
    if mp_constituency:
        mp = (
            MP.objects.filter(
                Q(constituency__code__iexact=mp_constituency)
                | Q(constituency__name__iexact=mp_constituency)
            )
            .select_related("constituency")
            .first()
        )

    # Fall back to name match
    if not mp and mp_name:
        mp = (
            MP.objects.filter(name__iexact=mp_name)
            .select_related("constituency")
            .first()
        )
        if not mp:
            mp = (
                MP.objects.filter(name__icontains=mp_name)
                .select_related("constituency")
                .first()
            )
            if not mp and len(mp_name) > 5:
                # Try each word of the name (skip short titles)
                for word in mp_name.split():
                    if len(word) > 4:
                        mp = (
                            MP.objects.filter(name__icontains=word)
                            .select_related("constituency")
                            .first()
                        )
                        if mp:
                            break

    if mp:
        if not result["mp_name"] or len(result["mp_name"]) < len(mp.name):
            result["mp_name"] = mp.name
        if not result["mp_constituency"]:
            result["mp_constituency"] = mp.constituency.name
        if not result["mp_party"]:
            result["mp_party"] = mp.party
        logger.debug("Resolved MP: %s (%s)", mp.name, mp.constituency.code)

    return result
