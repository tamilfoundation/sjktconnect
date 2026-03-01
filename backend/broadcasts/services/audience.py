"""
Audience filtering service for broadcasts.

Builds a subscriber queryset based on audience filter criteria.
School-based filters (state, constituency, ppd, enrolment, skm) work by
finding schools that match, then including subscribers whose email matches
a school email (i.e. @moe.edu.my contacts). Non-school subscribers are
included when no school-specific filters are applied.
"""

from django.db.models import QuerySet

from schools.models import School
from subscribers.models import Subscriber


def get_filtered_subscribers(filter_dict: dict) -> QuerySet[Subscriber]:
    """
    Filter active subscribers based on audience criteria.

    Supported filters:
    - category: Filter by subscription preference category
    - state: Filter subscribers whose subscribed schools are in this state
    - constituency: Filter by constituency code
    - ppd: Filter by PPD (district)
    - min_enrolment / max_enrolment: Filter by school enrolment range
    - skm: Filter by SKM eligibility (true/false)

    Returns a distinct queryset of active subscribers matching all criteria.
    """
    qs = Subscriber.objects.filter(is_active=True)

    if not filter_dict:
        return qs.distinct()

    # Category preference filter
    category = filter_dict.get("category", "")
    if category:
        qs = qs.filter(
            preferences__category=category,
            preferences__is_enabled=True,
        )

    # School-based filters — build a School queryset first
    school_filters = {}
    state = filter_dict.get("state", "")
    if state:
        school_filters["state"] = state

    constituency = filter_dict.get("constituency", "")
    if constituency:
        school_filters["constituency__code"] = constituency

    ppd = filter_dict.get("ppd", "")
    if ppd:
        school_filters["ppd"] = ppd

    min_enrolment = filter_dict.get("min_enrolment")
    if min_enrolment is not None and min_enrolment != "":
        school_filters["enrolment__gte"] = int(min_enrolment)

    max_enrolment = filter_dict.get("max_enrolment")
    if max_enrolment is not None and max_enrolment != "":
        school_filters["enrolment__lte"] = int(max_enrolment)

    skm = filter_dict.get("skm")
    if skm is not None and skm != "":
        # Accept bool or string "true"/"false"
        if isinstance(skm, str):
            school_filters["skm_eligible"] = skm.lower() == "true"
        else:
            school_filters["skm_eligible"] = bool(skm)

    if school_filters:
        # Find emails of schools matching the criteria
        school_emails = (
            School.objects.filter(**school_filters)
            .exclude(email="")
            .values_list("email", flat=True)
        )
        qs = qs.filter(email__in=school_emails)

    return qs.distinct()
