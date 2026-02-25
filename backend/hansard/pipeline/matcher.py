"""Match Hansard mentions to specific schools using alias table.

Two-pass matching:
1. **Exact match**: Look up normalised text against SchoolAlias.alias_normalized.
   Confidence = 100%.
2. **Trigram similarity**: For unmatched mentions, compare context against aliases
   using pg_trgm (PostgreSQL) or difflib.SequenceMatcher (SQLite fallback).
   Confidence = similarity * 100. If confidence < 80%, needs_review = True.

Usage:
    from hansard.pipeline.matcher import match_mentions
    results = match_mentions(mention_queryset)
"""

import logging
import re
from difflib import SequenceMatcher

from django.db import connection

from hansard.models import HansardMention, MentionedSchool, SchoolAlias
from hansard.pipeline.stop_words import STOP_WORDS, remove_stop_words

logger = logging.getLogger(__name__)

# Minimum trigram similarity to consider a match
TRIGRAM_THRESHOLD = 0.3

# Confidence below this → needs_review = True
REVIEW_THRESHOLD = 80


def _extract_school_name_candidates(text: str) -> list[str]:
    """Extract potential school name fragments from mention text.

    Finds school prefix patterns (SJK(T), SJKT, Sekolah Tamil, etc.)
    and extracts the words following them as candidate school names.
    The matcher's progressive shortening handles boundary detection —
    this function intentionally captures generously.

    Returns a list of candidate strings to match against aliases.
    """
    candidates = []
    lower = text.lower()

    # Find all school prefix positions
    prefix_re = re.compile(
        r"(?:sjk\s*\(t\)|sjkt|s\.j\.k\.?\s*\(t\)|"
        r"sekolah(?:\s+jenis\s+kebangsaan)?\s+(?:\(tamil\)|tamil))"
    )

    for m in prefix_re.finditer(lower):
        prefix = m.group().strip()
        rest = lower[m.end():].strip()

        # Extract word tokens after the prefix.
        # Stop at conjunctions/prepositions/verbs that signal end of name.
        _BOUNDARY_WORDS = {
            "dan", "and", "serta", "atau", "di", "yang", "untuk",
            "ini", "itu", "telah", "perlu", "akan", "dengan",
            "memerlukan", "mempunyai", "menghadapi", "termasuk",
            "adalah", "sebanyak", "seramai", "dalam",
        }
        name_words = []
        for word in rest.split():
            if word in _BOUNDARY_WORDS:
                break
            # Stop at currency amounts
            if word.startswith("rm") and len(word) > 2:
                break
            name_words.append(word)
            if len(name_words) >= 6:
                break

        if name_words:
            name = " ".join(name_words)
            candidates.append(f"{prefix} {name}")  # with prefix
            candidates.append(name)  # name part only

    return candidates


def _has_pg_trgm() -> bool:
    """Check if pg_trgm extension is available."""
    if connection.vendor != "postgresql":
        return False
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'"
        )
        return cursor.fetchone() is not None


def _trigram_similarity_pg(text: str, aliases: list[str]) -> list[tuple[str, float]]:
    """Use PostgreSQL pg_trgm for trigram similarity."""
    if not aliases:
        return []

    results = []
    with connection.cursor() as cursor:
        for alias in aliases:
            cursor.execute(
                "SELECT similarity(%s, %s)",
                [text, alias],
            )
            sim = cursor.fetchone()[0]
            if sim >= TRIGRAM_THRESHOLD:
                results.append((alias, float(sim)))

    return sorted(results, key=lambda x: x[1], reverse=True)


def _trigram_similarity_python(text: str, aliases: list[str]) -> list[tuple[str, float]]:
    """Python fallback using difflib.SequenceMatcher."""
    if not aliases:
        return []

    results = []
    for alias in aliases:
        sim = SequenceMatcher(None, text, alias).ratio()
        if sim >= TRIGRAM_THRESHOLD:
            results.append((alias, sim))

    return sorted(results, key=lambda x: x[1], reverse=True)


def _trigram_similarity(text: str, aliases: list[str]) -> list[tuple[str, float]]:
    """Route to pg_trgm or Python fallback."""
    if _has_pg_trgm():
        return _trigram_similarity_pg(text, aliases)
    return _trigram_similarity_python(text, aliases)


def match_single_mention(mention: HansardMention) -> list[dict]:
    """Match a single mention to schools.

    Returns a list of match dicts:
        {school_id, confidence, matched_by, matched_text, needs_review}
    """
    # Combine verbatim quote + context for candidate extraction
    full_text = " ".join(filter(None, [
        mention.context_before,
        mention.verbatim_quote,
        mention.context_after,
    ]))

    candidates = _extract_school_name_candidates(full_text)
    if not candidates:
        return []

    matches = []
    matched_school_ids = set()

    # Load all aliases into memory (faster than per-candidate DB queries)
    alias_map = {}  # alias_normalized → (school_id, alias)
    for sa in SchoolAlias.objects.select_related("school").all():
        alias_map[sa.alias_normalized] = (sa.school_id, sa.alias)

    all_alias_keys = list(alias_map.keys())

    for candidate in candidates:
        normalized = candidate.lower().strip()
        normalized = re.sub(r"\s+", " ", normalized)

        # Pass 1: Exact match — try full candidate, then progressively
        # shorter (trim words from right) to handle regex over-capture.
        # E.g. "sjk(t) ladang bikam memerlukan" → try that, then
        # "sjk(t) ladang bikam", then "sjk(t) ladang".
        exact_found = False
        words = normalized.split()
        for end in range(len(words), 0, -1):
            subset = " ".join(words[:end])
            if subset in alias_map:
                school_id, alias_text = alias_map[subset]
                if school_id not in matched_school_ids:
                    matched_school_ids.add(school_id)
                    matches.append({
                        "school_id": school_id,
                        "confidence": 100,
                        "matched_by": MentionedSchool.MatchMethod.EXACT,
                        "matched_text": candidate,
                        "needs_review": False,
                    })
                exact_found = True
                break

        if exact_found:
            continue

        # Pass 2: Trigram similarity (with stop words removed)
        cleaned = remove_stop_words(normalized)
        if not cleaned:
            continue

        # Compare against aliases with stop words removed
        cleaned_aliases = {}
        for alias_norm, (school_id, alias_text) in alias_map.items():
            if school_id in matched_school_ids:
                continue
            cleaned_alias = remove_stop_words(alias_norm)
            if cleaned_alias:
                cleaned_aliases[cleaned_alias] = (school_id, alias_text, alias_norm)

        sim_results = _trigram_similarity(cleaned, list(cleaned_aliases.keys()))

        for alias_cleaned, sim in sim_results:
            if alias_cleaned not in cleaned_aliases:
                continue
            school_id, alias_text, alias_norm = cleaned_aliases[alias_cleaned]
            if school_id in matched_school_ids:
                continue

            confidence = round(sim * 100, 2)
            matched_school_ids.add(school_id)
            matches.append({
                "school_id": school_id,
                "confidence": confidence,
                "matched_by": MentionedSchool.MatchMethod.TRIGRAM,
                "matched_text": candidate,
                "needs_review": confidence < REVIEW_THRESHOLD,
            })
            break  # Best match only per candidate

    return matches


def match_mentions(mentions=None):
    """Match all unmatched mentions to schools.

    Args:
        mentions: QuerySet of HansardMention. If None, processes all
                  mentions that have no MentionedSchool records yet.

    Returns:
        dict with counts: {matched, unmatched, needs_review, total}
    """
    if mentions is None:
        mentions = HansardMention.objects.filter(
            matched_schools__isnull=True
        )

    total = mentions.count()
    matched_count = 0
    review_count = 0

    for mention in mentions:
        results = match_single_mention(mention)
        for result in results:
            MentionedSchool.objects.update_or_create(
                mention=mention,
                school_id=result["school_id"],
                defaults={
                    "confidence_score": result["confidence"],
                    "matched_by": result["matched_by"],
                    "matched_text": result["matched_text"],
                    "needs_review": result["needs_review"],
                },
            )
            matched_count += 1
            if result["needs_review"]:
                review_count += 1

    unmatched = total - mentions.filter(matched_schools__isnull=False).distinct().count()

    logger.info(
        "Matching complete: %d/%d mentions matched, %d need review",
        total - unmatched, total, review_count,
    )

    return {
        "total": total,
        "matched": total - unmatched,
        "unmatched": unmatched,
        "needs_review": review_count,
    }
