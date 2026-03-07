"""School name repair utilities.

Attempts to match unlinked school names by:
1. Stripping trailing punctuation
2. Removing commas within the name
3. Dropping filler words (di, dan)
4. Fuzzy matching against the alias table
"""

import re
import logging
from difflib import SequenceMatcher

from hansard.models import SchoolAlias

logger = logging.getLogger(__name__)

_PREFIX_RE = re.compile(
    r"^(?:SJK\s*\(T\)|SJKT|S\.J\.K\.?\s*\(T\)|"
    r"Sekolah(?:\s+Jenis\s+Kebangsaan)?\s+(?:\(Tamil\)|Tamil))\s*",
    re.IGNORECASE,
)

_FILLER_WORDS = {"di", "dan"}

_FUZZY_THRESHOLD = 0.7


def repair_school_name(name: str) -> dict | None:
    """Attempt to match a school name that failed standard matching.

    Args:
        name: The unlinked school name (e.g., "SJK(T) Ladang, Mentakab")

    Returns:
        dict with keys: school_code, repaired_name, original_name, method
        or None if no match found.
    """
    stripped = name.strip().rstrip(".,;:!?)")
    match = _PREFIX_RE.search(stripped)
    if not match:
        return None

    suffix = stripped[match.end():].strip()
    if not suffix:
        return None

    candidates = _generate_repair_candidates(suffix)

    for candidate, method in candidates:
        alias = SchoolAlias.objects.filter(
            alias_normalized=candidate.lower(),
        ).select_related("school").first()
        if alias:
            repaired = f"SJK(T) {candidate}"
            return {
                "school_code": alias.school.moe_code,
                "repaired_name": repaired,
                "original_name": name,
                "method": method,
            }

    fuzzy_result = _fuzzy_match(suffix)
    if fuzzy_result:
        return fuzzy_result | {"original_name": name}

    return None


def _generate_repair_candidates(suffix: str) -> list[tuple[str, str]]:
    """Generate candidate names from transformations."""
    candidates = []

    candidates.append((suffix, "exact"))

    no_commas = suffix.replace(",", "").strip()
    no_commas = re.sub(r"\s+", " ", no_commas)
    if no_commas != suffix:
        candidates.append((no_commas, "comma-removal"))

    words = no_commas.split()
    filtered = [w for w in words if w.lower() not in _FILLER_WORDS]
    filtered_name = " ".join(filtered)
    if filtered_name != no_commas:
        candidates.append((filtered_name, "filler-removal"))

    return candidates


def _fuzzy_match(suffix: str) -> dict | None:
    """Fuzzy match against all aliases using SequenceMatcher."""
    target = suffix.lower().replace(",", "").strip()
    target = re.sub(r"\s+", " ", target)

    best_score = 0
    best_alias = None

    for alias in SchoolAlias.objects.select_related("school").iterator():
        score = SequenceMatcher(None, target, alias.alias_normalized).ratio()
        if score > best_score:
            best_score = score
            best_alias = alias

    if best_score >= _FUZZY_THRESHOLD and best_alias:
        return {
            "school_code": best_alias.school.moe_code,
            "repaired_name": f"SJK(T) {best_alias.alias}",
            "method": f"fuzzy-{best_score:.0%}",
        }

    return None
