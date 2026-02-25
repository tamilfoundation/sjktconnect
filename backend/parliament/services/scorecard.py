"""MP Scorecard aggregation service.

Reads all analysed HansardMentions, groups by MP, and creates/updates
MPScorecard records with aggregated counts.
"""

import logging

from django.db.models import Count, Max, Q, Sum

from hansard.models import HansardMention
from parliament.models import MPScorecard
from schools.models import Constituency, School

logger = logging.getLogger(__name__)


def update_all_scorecards():
    """Recalculate all MP scorecards from scratch.

    Groups analysed mentions by mp_name, then creates or updates
    MPScorecard records with totals. Also caches school_count and
    total_enrolment from the constituency.

    Returns:
        dict with counts: created, updated, deleted.
    """
    # Only consider mentions that have been analysed (have an mp_name)
    analysed = HansardMention.objects.exclude(mp_name="")

    # Group by MP name — aggregate counts
    mp_stats = (
        analysed
        .values("mp_name", "mp_constituency", "mp_party")
        .annotate(
            total=Count("id"),
            substantive=Count("id", filter=Q(significance__gte=3)),
            questions=Count("id", filter=Q(mention_type="QUESTION")),
            commitments=Count(
                "id",
                filter=Q(mention_type="COMMITMENT") | Q(sentiment="PROMISING"),
            ),
            last_date=Max("sitting__sitting_date"),
        )
        .order_by("-total")
    )

    seen_keys = set()
    created = 0
    updated = 0

    for stat in mp_stats:
        mp_name = stat["mp_name"]
        constituency_name = stat["mp_constituency"]

        # Try to resolve constituency
        constituency = _resolve_constituency(constituency_name)

        # Build school stats from constituency
        school_count = 0
        total_enrolment = 0
        if constituency:
            school_agg = School.objects.filter(
                constituency=constituency, is_active=True,
            ).aggregate(
                count=Count("moe_code"),
                enrolment=Sum("enrolment"),
            )
            school_count = school_agg["count"] or 0
            total_enrolment = school_agg["enrolment"] or 0

        scorecard, is_new = MPScorecard.objects.update_or_create(
            mp_name=mp_name,
            constituency=constituency,
            defaults={
                "party": stat["mp_party"] or "",
                "total_mentions": stat["total"],
                "substantive_mentions": stat["substantive"],
                "questions_asked": stat["questions"],
                "commitments_made": stat["commitments"],
                "last_mention_date": stat["last_date"],
                "school_count": school_count,
                "total_enrolment": total_enrolment,
            },
        )

        seen_keys.add(scorecard.pk)
        if is_new:
            created += 1
        else:
            updated += 1

    # Delete scorecards for MPs no longer in the data
    deleted_count, _ = (
        MPScorecard.objects.exclude(pk__in=seen_keys).delete()
    )

    logger.info(
        "Scorecards updated: %s created, %s updated, %s deleted",
        created, updated, deleted_count,
    )
    return {"created": created, "updated": updated, "deleted": deleted_count}


def _resolve_constituency(name):
    """Try to find a Constituency by name (case-insensitive).

    Returns Constituency or None.
    """
    if not name:
        return None

    # Try exact match first (case-insensitive on name)
    try:
        return Constituency.objects.get(name__iexact=name)
    except Constituency.DoesNotExist:
        pass
    except Constituency.MultipleObjectsReturned:
        return Constituency.objects.filter(name__iexact=name).first()

    # Try matching on "code name" pattern like "P140 Segamat"
    if " " in name:
        parts = name.split(None, 1)
        if parts[0].startswith("P"):
            try:
                return Constituency.objects.get(code__iexact=parts[0])
            except Constituency.DoesNotExist:
                pass

    # Try contains as last resort
    matches = Constituency.objects.filter(name__icontains=name)
    if matches.count() == 1:
        return matches.first()

    return None
