"""Gemini Flash API client for analysing news articles about Tamil schools.

Sends article title + body text (truncated to ~3000 chars) to Gemini,
receives back a JSON object with:
  relevance_score, sentiment, summary, mentioned_schools, is_urgent, urgent_reason

Follows the same pattern as parliament/services/gemini_client.py.
"""

import json
import logging
import os

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# Valid enum values for validation
SENTIMENTS = {"POSITIVE", "NEGATIVE", "NEUTRAL", "MIXED"}

ANALYSIS_PROMPT = """\
You are analysing a news article that may be about Malaysian Tamil schools (SJK(T)).

Analyse the article and return a JSON object with these fields:

- relevance_score: Integer 1-5
  - 1: No mention of Tamil schools, unrelated
  - 2: Passing mention, not the focus
  - 3: Mentions Tamil schools as part of a broader topic
  - 4: Primarily about Tamil schools
  - 5: Entirely focused on Tamil schools, major news

- sentiment: One of POSITIVE, NEGATIVE, NEUTRAL, MIXED
  - POSITIVE: Good news for Tamil schools (funding, improvements, recognition)
  - NEGATIVE: Bad news (closures, problems, neglect, declining enrolment)
  - NEUTRAL: Factual reporting without clear positive/negative slant
  - MIXED: Contains both positive and negative aspects

- summary: 2-3 sentence English summary focused on what this means for Tamil schools.
  Be specific about names, locations, and figures mentioned.

- mentioned_schools: Array of objects for SJK(T) / Tamil schools ONLY.
  Do NOT include non-Tamil schools (SK, SMK, SJK(C), SRJK(C), etc.).
  Each object has:
  - name: School name in ENGLISH/ROMANISED form as "SJK(T) <Name>" (string).
    If the article is in Tamil, transliterate the school name to English.
    Examples: "சரஸ்வதி தமிழ்ப்பள்ளி" → "SJK(T) Saraswathy",
    "கின்ராரா தோட்டத் தமிழ்ப்பள்ளி" → "SJK(T) Ladang Kinrara",
    "எல்ஃபில் தோட்டத் தமிழ்ப்பள்ளி" → "SJK(T) Ladang Elphil",
    "ரந்தாவ் தமிழ்ப்பள்ளி" → "SJK(T) Rantau".
    Note: "தோட்ட" means "Ladang" (estate).
  - moe_code: MOE code if identifiable (string, or "" if unknown)
  Keep empty array [] if no specific Tamil schools are named.

- is_urgent: Boolean. True ONLY if the article reports:
  - School closure or merger threat
  - Safety crisis (building collapse, flood, etc.)
  - Student/teacher safety issue
  - Funding cut or budget crisis affecting operations
  - Political controversy requiring immediate response

- urgent_reason: If is_urgent is true, one sentence explaining why.
  Empty string if not urgent.

Return ONLY valid JSON, no markdown fences, no extra text.

--- ARTICLE ---
Title: {title}

{body}
--- END ARTICLE ---
"""


def _get_client():
    """Create a Gemini API client with the API key."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY environment variable is not set. "
            "Get one from https://aistudio.google.com/apikey"
        )
    return genai.Client(api_key=api_key)


def _build_body(article):
    """Build a token-budgeted body from an article.

    Uses title + first ~3000 chars of body text.
    """
    body = article.body_text.strip()
    max_chars = 3000
    if len(body) > max_chars:
        body = body[:max_chars] + "..."
    return body


def _validate_response(data):
    """Validate and normalise the Gemini response fields.

    Returns a clean dict with all expected fields, filling in defaults
    for any missing or invalid values.
    """
    result = {
        "relevance_score": data.get("relevance_score"),
        "sentiment": str(data.get("sentiment", "NEUTRAL")).strip().upper(),
        "summary": str(data.get("summary", "")).strip(),
        "mentioned_schools": data.get("mentioned_schools", []),
        "is_urgent": bool(data.get("is_urgent", False)),
        "urgent_reason": str(data.get("urgent_reason", "")).strip(),
    }

    # Clamp sentiment to valid values
    if result["sentiment"] not in SENTIMENTS:
        result["sentiment"] = "NEUTRAL"

    # Clamp relevance_score to 1-5
    try:
        score = int(result["relevance_score"])
        result["relevance_score"] = max(1, min(5, score))
    except (TypeError, ValueError):
        result["relevance_score"] = 1

    # Ensure mentioned_schools is a list
    if not isinstance(result["mentioned_schools"], list):
        result["mentioned_schools"] = []

    # Clean up urgent_reason if not urgent
    if not result["is_urgent"]:
        result["urgent_reason"] = ""

    return result


def analyse_article(article):
    """Analyse a single NewsArticle using Gemini Flash.

    Args:
        article: NewsArticle instance with body_text populated.

    Returns:
        dict with validated analysis fields, or None on failure.

    Raises:
        ValueError: If GEMINI_API_KEY is not set.
    """
    client = _get_client()

    body = _build_body(article)
    prompt = ANALYSIS_PROMPT.format(title=article.title, body=body)

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )
        raw_text = response.text.strip()
    except Exception:
        logger.exception("Gemini API call failed for article %s", article.pk)
        return None

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        logger.error(
            "Gemini returned invalid JSON for article %s: %s",
            article.pk, raw_text[:200],
        )
        return None

    result = _validate_response(data)
    result["raw_response"] = data
    return result


def _strip_prefix(name):
    """Strip common school type prefixes to get the distinctive part.

    Handles both English and Tamil prefixes:
    - "SJKT Kerajaan" -> "Kerajaan"
    - "SJK(T) Ladang Highlands" -> "Ladang Highlands"
    - "சரஸ்வதி தமிழ்ப்பள்ளி" -> "சரஸ்வதி"
    - "தேசிய வகை சரஸ்வதி தமிழ்ப்பள்ளி" -> "சரஸ்வதி"
    """
    import re
    # English prefixes (handles "SJK(T)", "SJK (T)", "SJKT", etc.)
    name = re.sub(
        r"^(?:SJK\s*\(?\s*T\s*\)?|SJKT|SRK\s*\(T\)|SRJK\s*\(T\))\s*",
        "", name, flags=re.IGNORECASE,
    ).strip()
    # Tamil suffixes: தமிழ்ப்பள்ளி (Tamil school)
    name = re.sub(
        r"\s*(?:தேசிய\s+வகை\s+)?தமிழ்ப்பள்ளி\s*$",
        "", name,
    ).strip()
    # Tamil prefixes: தேசிய வகை (national type)
    name = re.sub(
        r"^தேசிய\s+வகை\s*",
        "", name,
    ).strip()
    return name


# Common abbreviation variants in Malaysian school names
_ABBREV_MAP = {
    "Ladang": "Ldg",
    "Sungai": "Sg",
    "Kampung": "Kg",
    "Jalan": "Jln",
    "Estate": "Ldg",
    "Island": "Pulau",
    "East": "Timur",
    "West": "Barat",
    "South": "Selatan",
    "North": "Utara",
}
# Build reverse map too (Ldg → Ladang, Timur → East, etc.)
_ABBREV_REVERSE = {v: k for k, v in _ABBREV_MAP.items()}
_ABBREV_ALL = {**_ABBREV_MAP, **_ABBREV_REVERSE}

# Words to strip from Gemini's school names before matching
_NOISE_WORDS = {
    "tamil", "school", "primary", "in", "at", "the", "sekolah",
}


def _normalise_for_matching(text):
    """Normalise a school name for fuzzy matching.

    - Strips noise words (Tamil, School, Estate, in, at)
    - Strips commas and location suffixes after commas
    - Normalises apostrophes (curly → straight)
    - Strips quotes and parenthesised numbers like (1) → 1
    - Swaps abbreviation variants (Ladang↔Ldg, East↔Timur, etc.)
    """
    import re
    # Strip everything after comma (location qualifiers like ", Brickfields")
    text = text.split(",")[0].strip()
    # Normalise apostrophes
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", "'").replace("\u201d", "'")
    # Strip quotes around words: 'Barat' → Barat
    text = re.sub(r"['\"]", "", text)
    # Remove noise words
    words = text.split()
    words = [w for w in words if w.lower() not in _NOISE_WORDS]
    # Swap abbreviation variants
    result = []
    for w in words:
        replaced = False
        for full, abbrev in _ABBREV_ALL.items():
            if w.lower() == full.lower():
                result.append(abbrev)
                replaced = True
                break
        if not replaced:
            result.append(w)
    return " ".join(result)


def _generate_name_variants(distinctive):
    """Generate multiple search variants from a distinctive name.

    Returns a list of strings to try matching against the database.
    E.g. "Ladang Boh 1" → ["Ladang Boh 1", "Ldg Boh 1", "Ldg Boh (1)",
    "Ladang Boh (1)"]
    """
    import re
    variants = [distinctive]

    # Normalised form
    normalised = _normalise_for_matching(distinctive)
    if normalised != distinctive:
        variants.append(normalised)

    # Add parenthesised number variant: "Boh 1" → "Boh (1)"
    num_match = re.search(r"\s(\d+)$", distinctive)
    if num_match:
        paren_form = distinctive[:num_match.start()] + f" ({num_match.group(1)})"
        variants.append(paren_form)
        norm_paren = _normalise_for_matching(paren_form)
        if norm_paren not in variants:
            variants.append(norm_paren)

    # Strip "Jalan"/"Jln" prefix: "Jalan Fletcher" → "Fletcher"
    stripped_jalan = re.sub(
        r"^(?:Jalan|Jln)\s+", "", distinctive, flags=re.IGNORECASE
    ).strip()
    if stripped_jalan != distinctive:
        variants.append(stripped_jalan)

    return list(dict.fromkeys(variants))  # dedupe, preserve order


def _resolve_school_codes(mentioned_schools, article=None):
    """Match mentioned school names against the database to fill in moe_codes.

    Strips SJKT/SJK(T) prefixes and uses multiple matching strategies:
    1. Exact match on short_name
    2. SJK(T) + distinctive part exact match
    3. Partial (icontains) match on distinctive part
    4. Name variant generation (abbreviation swaps, number formats)
    5. Multi-word AND search
    6. Location-based disambiguation for multiple matches
    """
    from django.db.models import Q
    from schools.models import School

    # Build location context from article text for disambiguation
    location_text = ""
    if article:
        location_text = f"{article.title} {article.body_text}".lower()

    resolved = []
    for entry in mentioned_schools:
        name = entry.get("name", "").strip()
        code = entry.get("moe_code", "").strip()
        if not name:
            continue

        # If Gemini already provided a code, verify it exists
        if code:
            if School.objects.filter(moe_code=code).exists():
                resolved.append({"name": name, "moe_code": code})
                continue

        # Extract the distinctive part (e.g. "Kerajaan" from "SJKT Kerajaan")
        distinctive = _strip_prefix(name)

        candidates = School.objects.none()

        # Strategy 1: Exact match on short_name as given
        candidates = School.objects.filter(short_name__iexact=name)

        # Strategy 2: SJK(T) + distinctive exact match
        if not candidates.exists() and distinctive:
            candidates = School.objects.filter(
                short_name__iexact=f"SJK(T) {distinctive}"
            )

        # Strategy 3: Try all name variants (abbreviations, number formats, etc.)
        if not candidates.exists() and distinctive:
            for variant in _generate_name_variants(distinctive):
                candidates = School.objects.filter(
                    short_name__iexact=f"SJK(T) {variant}"
                )
                if candidates.exists():
                    break
                # Also try partial match
                candidates = School.objects.filter(
                    short_name__icontains=variant
                )
                if candidates.exists():
                    break

        # Strategy 4: Multi-word AND search (catches "Melaka (Kubu)" from "Melaka Kubu")
        if not candidates.exists() and distinctive:
            # Use normalised form for word search
            normalised = _normalise_for_matching(distinctive)
            words = [w for w in normalised.split() if len(w) >= 3]
            if len(words) >= 2:
                q = Q(short_name__icontains=words[0])
                for w in words[1:]:
                    q &= Q(short_name__icontains=w)
                candidates = School.objects.filter(q)

        # Strategy 5: Last resort — try just the most distinctive word (longest)
        # Only use words >= 6 chars and skip common geographic terms
        if not candidates.exists() and distinctive:
            _GENERIC_WORDS = {
                "ladang", "estate", "jalan", "bandar", "taman", "kampung",
                "sungai", "pulau", "island", "teluk", "bukit", "tanjung",
                "bagan", "barat", "timur", "selatan", "utara", "bidor",
                "tangkak", "convent",
            }
            words = [
                w for w in distinctive.split()
                if len(w) >= 6 and w.lower() not in _GENERIC_WORDS
            ]
            words.sort(key=len, reverse=True)
            for w in words[:2]:
                candidates = School.objects.filter(short_name__icontains=w)
                if candidates.count() == 1:
                    break
                # Don't use ambiguous single-word matches
                candidates = School.objects.none()

        # Resolve candidates
        if candidates.count() == 1:
            match = candidates.first()
            resolved.append({"name": match.short_name, "moe_code": match.moe_code})
        elif candidates.count() > 1 and location_text:
            # Disambiguate using location clues from article
            match = _disambiguate_by_location(candidates, location_text)
            resolved.append({"name": match.short_name, "moe_code": match.moe_code})
        elif candidates.exists():
            # Multiple matches, no location context — pick first but log it
            match = candidates.first()
            logger.warning(
                "Ambiguous school match for '%s': %d candidates, picked %s",
                name, candidates.count(), match.moe_code,
            )
            resolved.append({"name": match.short_name, "moe_code": match.moe_code})
        else:
            resolved.append({"name": name, "moe_code": ""})

    return resolved


def _disambiguate_by_location(candidates, location_text):
    """Pick the best school from multiple candidates using article text.

    Scores each candidate by how many of its location fields (state, city,
    ppd) appear in the article text. Returns the highest-scoring match.
    """
    best = None
    best_score = -1

    for school in candidates:
        score = 0
        if school.state and school.state.lower() in location_text:
            score += 2
        if school.city and school.city.lower() in location_text:
            score += 3  # City is more specific, higher weight
        if school.ppd and school.ppd.lower() in location_text:
            score += 1
        if score > best_score:
            best_score = score
            best = school

    return best


def apply_analysis(article, analysis):
    """Apply validated analysis dict to a NewsArticle and save.

    Sets status to ANALYSED and populates all AI fields.

    Args:
        article: NewsArticle instance.
        analysis: dict from analyse_article().
    """
    from newswatch.models import NewsArticle as NA

    article.relevance_score = analysis["relevance_score"]
    article.sentiment = analysis["sentiment"]
    article.ai_summary = analysis["summary"]
    article.mentioned_schools = _resolve_school_codes(
        analysis["mentioned_schools"], article=article
    )
    article.is_urgent = analysis["is_urgent"]
    article.urgent_reason = analysis["urgent_reason"]
    article.ai_raw_response = analysis.get("raw_response", {})
    article.status = NA.ANALYSED

    # Auto-approve articles with relevance_score >= 3
    if article.relevance_score and article.relevance_score >= 3:
        article.review_status = NA.APPROVED

    article.save(update_fields=[
        "relevance_score", "sentiment", "ai_summary", "mentioned_schools",
        "is_urgent", "urgent_reason", "ai_raw_response", "status",
        "review_status", "updated_at",
    ])


def analyse_pending_articles(batch_size=10):
    """Analyse all EXTRACTED articles that haven't been analysed yet.

    Args:
        batch_size: Maximum number of articles to process in one run.

    Returns:
        dict with counts: {"analysed": int, "failed": int, "skipped": int}
    """
    from newswatch.models import NewsArticle as NA

    articles = NA.objects.filter(status=NA.EXTRACTED).order_by("created_at")[:batch_size]

    counts = {"analysed": 0, "failed": 0, "skipped": 0}

    for article in articles:
        if not article.body_text.strip():
            counts["skipped"] += 1
            continue

        analysis = analyse_article(article)
        if analysis is None:
            counts["failed"] += 1
            continue

        apply_analysis(article, analysis)
        counts["analysed"] += 1
        logger.info(
            "Analysed article %s: relevance=%s, urgent=%s",
            article.pk, analysis["relevance_score"], analysis["is_urgent"],
        )

    return counts
