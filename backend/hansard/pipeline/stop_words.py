"""Stop words excluded from fuzzy school name matching.

These high-frequency words appear in almost every school name or Hansard
context and add noise to trigram similarity. Removing them before
comparison improves match precision.

The lists are intentionally short — only words that cause false positives.
"""

# Common prefixes/suffixes in SJK(T) school names
SCHOOL_NAME_STOP_WORDS = {
    "sjk",
    "sjkt",
    "sjk(t)",
    "sekolah",
    "jenis",
    "kebangsaan",
    "tamil",
    "rendah",
    "primary",
    "school",
}

# Location words that appear in many school names
LOCATION_STOP_WORDS = {
    "ladang",       # estate/plantation
    "estate",
    "jalan",        # road
    "kampung",      # village
    "taman",        # housing estate
    "lorong",       # lane
    "bandar",       # town
    "pekan",        # small town
    "felda",        # FELDA scheme
    "kg",           # abbreviation for kampung
}

# Common Malay words that cause false positive trigram matches
# e.g. "juga" → "Ldg Jugra", "khususnya" → "Jalan Khalidi"
MALAY_STOP_WORDS = {
    "juga",         # also
    "khususnya",    # especially
    "baharu",       # new
    "bersama",      # together
}

# All stop words combined
STOP_WORDS = SCHOOL_NAME_STOP_WORDS | LOCATION_STOP_WORDS | MALAY_STOP_WORDS


def remove_stop_words(text: str) -> str:
    """Remove stop words from normalised text for fuzzy matching.

    Args:
        text: Normalised (lowercased) text.

    Returns:
        Text with stop words removed, extra spaces collapsed.
    """
    words = text.split()
    filtered = [w for w in words if w not in STOP_WORDS]
    return " ".join(filtered)
