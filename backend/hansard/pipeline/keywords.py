"""Keyword list for detecting Tamil school mentions in Hansard text.

Keywords are split into two tiers:
- PRIMARY: High-confidence — these almost certainly refer to Tamil schools
- SECONDARY: Need context — common terms that may appear in non-school contexts
"""

# Primary keywords — high confidence, always search
PRIMARY_KEYWORDS = [
    "sjk(t)",
    "sjkt",
    "s.j.k.(t)",
    "s.j.k(t)",
    "sekolah jenis kebangsaan tamil",
    "sekolah jenis kebangsaan (tamil)",
    "sekolah tamil",
    "tamil school",
    "tamil schools",
    "tamil primary school",
    "tamil primary schools",
    "sekolah rendah tamil",
]

# Secondary keywords — need surrounding context to confirm relevance
SECONDARY_KEYWORDS = [
    "vernacular school",
    "vernacular schools",
    "sekolah vernakular",
    "pendidikan tamil",
    "tamil education",
    "murid tamil",
    "pelajar tamil",
]


def get_all_keywords():
    """Return all keywords (primary + secondary) as a flat list."""
    return PRIMARY_KEYWORDS + SECONDARY_KEYWORDS


def get_primary_keywords():
    """Return only high-confidence keywords."""
    return list(PRIMARY_KEYWORDS)


def get_school_names_from_db():
    """Load school short names from the database for matching.

    Returns a list of short names like 'SJK(T) Ladang Bikam'.
    These are used as additional search terms in the keyword search.
    """
    from schools.models import School

    return list(
        School.objects.filter(is_active=True)
        .values_list("short_name", flat=True)
    )
