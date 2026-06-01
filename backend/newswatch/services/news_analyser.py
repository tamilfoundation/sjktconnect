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

# Sprint 24 task #1a — classifieds/real-estate domains whose articles
# surface SJK(T) only as amenity bullets, location names, or directory
# entries. Filter before Gemini so we don't spend tokens classifying
# property listings, and so genuinely off-topic articles cannot reach
# subscribers via the auto-approve-at-relevance-≥3 path.
# Added after the 2026-05-03 render audit found that 4 of 5 April-digest
# news cards were real-estate listings from edgeprop.my.
DOMAIN_BLOCKLIST = frozenset({
    "edgeprop.my",
    "propertyguru.com.my",
    "iproperty.com.my",
    "mudah.my",
})

ANALYSIS_PROMPT = """\
You are analysing a news article that may be about Malaysian Tamil schools (SJK(T)).

Analyse the article and return a JSON object with these fields:

- relevance_score: Integer 1-5
  Score the article on whether Tamil schools are the SUBJECT MATTER, not
  on whether the words "SJK(T)" or "Tamil school" merely appear in the
  text. A real-estate listing that mentions "SJK(T) school nearby" as an
  amenity scores 1, not 3 — the article is about a property, not about a
  school. A restaurant review that gives directions past a Tamil school
  scores 1, not 2.
  - 1: Tamil schools not mentioned, OR mentioned only as a location
       landmark / amenity bullet / address fragment / directory entry.
       The article's subject is unrelated (property listing, restaurant
       review, traffic news, etc.).
  - 2: Tamil schools mentioned in passing in an article whose primary
       subject is something else (general education policy, an Indian-
       community story, political coverage). Reader learns nothing
       specific about SJK(T).
  - 3: Tamil schools are a meaningful part of a broader story; the
       article includes substantive content about SJK(T) issues even if
       it also covers other topics.
  - 4: Primarily about Tamil schools — most paragraphs discuss SJK(T)
       people, institutions, or issues.
  - 5: Entirely focused on Tamil schools (e.g. one named school's
       redevelopment, a SJK(T)-only policy, a sector-wide story).
  Articles scoring ≥3 are auto-published to subscribers; ≤2 are
  auto-rejected. Err toward the lower score when uncertain.

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

- is_urgent: Boolean. Decide in TWO steps. Default to false.

  STEP 1 — Does the article contain ANY of these three triggers?
    (a) A specific named SJK(T) school confirmed closing or merging in
        the next 30 days, announced in THIS article (not a trend, not a
        historical reference).
    (b) An active emergency at a named SJK(T) right now: building
        collapse, fire, flood damage, mass illness, structural failure.
        NOT planned repairs, announced rebuilds, or chronic conditions.
    (c) A government decision announced in THIS article that will
        terminate or restrict SJK(T) operations within 30 days.
        Must be a binding restriction, NOT a permissive guideline,
        NOT a general education policy, NOT a reiteration of an
        existing policy.

  If STEP 1 is "no" for all three, set is_urgent=false and stop here.

  STEP 2 — If one of the triggers matched, answer both questions:
    Q1: Does the Tamil community need to ACT in the next 7 days to
        change or influence the outcome? If the decision is already
        final and irreversible, the answer is NO — it's news, not
        an alert.
    Q2: Is the trigger the PRIMARY subject of the article, not a
        passing mention, sidebar, or digression from the main topic?

  Set is_urgent=true ONLY if BOTH Q1 and Q2 are "yes".

  Examples that are NOT urgent (set is_urgent=false):
  - "Heat closure policy permits HMs to shut schools when >37°C."
    Permissive guideline — HMs gain autonomy, nothing needs to change.
  - "SJK(T) Gopeng's 80-year-old building to be rebuilt under RM14.5M
    project." The problem is being solved; this is good news.
  - "SJK(T) X enrolment dropping for 5th consecutive year."
    Chronic trend, not an event; no 7-day action window exists.
  - "Deputy Minister visits SJK(T) Y and announces routine funding."
    Routine visit, not an emergency.
  - "Award controversy involving a Tamil school."
    Advocacy topic, not a crisis requiring community action.
  - "MoE announces general curriculum review affecting all schools."
    General policy, not SJK(T)-specific restriction.

  Examples that ARE urgent (set is_urgent=true):
  - "SJK(T) X will close on 1 June; parents have until 15 May to
    appeal." Named school, 30-day window, actionable deadline,
    primary subject.
  - "SJK(T) Y roof collapsed overnight; 200 students displaced."
    Active emergency, named school, primary subject.
  - "Parliament to vote next Tuesday on bill restricting SJK(T)
    funding." Imminent binding decision, 7-day action window.

- urgent_reason: If is_urgent is true, one sentence explaining which
  trigger (a/b/c) matched and why the 7-day action window applies.
  Empty string if not urgent.

Return ONLY valid JSON, no markdown fences, no extra text.

--- ARTICLE ---
Title: {title}

{body}
--- END ARTICLE ---
"""

VERIFY_URGENT_PROMPT = """\
You are a strict editorial reviewer checking whether an alert should be
sent to 300+ Tamil school community subscribers as URGENT.

A previous analysis flagged this article as urgent. Your job is to
double-check. Err on the side of NOT urgent. The urgent classification
should be rare — roughly one article per month.

Article title: {title}

Article summary: {summary}

Reason given for urgency: {reason}

An alert is URGENT only if ALL of the following are true:
1. A specific named SJK(T) school is involved (not Tamil schools in general).
2. There is an active emergency, confirmed imminent closure, or binding
   government restriction taking effect within 30 days.
3. The community can still influence the outcome by acting within 7 days.
4. This is the primary subject of the article, not a passing mention.

If ANY of the four is not clearly true, the alert is NOT urgent.

Return a JSON object:
{{
  "confirmed": boolean,
  "reason": "one-sentence explanation of your verdict"
}}

Return ONLY valid JSON. No markdown fences.
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


def is_blocklisted_url(url: str) -> bool:
    """Return True if the URL's host is in DOMAIN_BLOCKLIST.

    Strips a leading "www." and lowercases the host for comparison.
    Returns False for empty or unparseable URLs.
    """
    from urllib.parse import urlparse
    if not url:
        return False
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return False
    if host.startswith("www."):
        host = host[4:]
    return host in DOMAIN_BLOCKLIST


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


def _verify_urgency(client, article, analysis):
    """Second-pass check that confirms urgent classification.

    When the first pass sets is_urgent=True, send a narrow verification
    prompt to a fresh Gemini call. If the verifier disagrees, downgrade
    is_urgent to False and blank urgent_reason. The original reason and
    verifier verdict are captured in analysis["raw_response"] for audit.

    Args:
        client: genai.Client instance.
        article: NewsArticle instance.
        analysis: validated analysis dict from _validate_response.

    Returns:
        The analysis dict, possibly with is_urgent downgraded.
    """
    if not analysis["is_urgent"]:
        return analysis

    prompt = VERIFY_URGENT_PROMPT.format(
        title=article.title,
        summary=analysis["summary"] or "(no summary)",
        reason=analysis["urgent_reason"] or "(no reason given)",
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0,
            ),
        )
        verdict = json.loads(response.text.strip())
    except Exception:
        logger.exception(
            "Urgency verification call failed for article %s — keeping first-pass verdict",
            article.pk,
        )
        return analysis

    confirmed = bool(verdict.get("confirmed", False))
    verify_reason = str(verdict.get("reason", "")).strip()

    # Attach audit trail regardless of outcome
    raw = analysis.setdefault("raw_response", {})
    raw["urgent_verification"] = {
        "confirmed": confirmed,
        "reason": verify_reason,
        "first_pass_reason": analysis["urgent_reason"],
    }

    if not confirmed:
        logger.info(
            "Article %s urgency downgraded. First-pass: %s. Verifier: %s",
            article.pk, analysis["urgent_reason"], verify_reason,
        )
        analysis["is_urgent"] = False
        analysis["urgent_reason"] = ""

    return analysis


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
    result = _verify_urgency(client, article, result)
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

    # Bridge letter↔digit boundaries: "PJS1" ⇄ "PJS 1", "Boh1" ⇄ "Boh 1".
    # Article text and MOE names disagree on whether a section/lot number is
    # spaced or joined, so try both spellings against the database.
    spaced = re.sub(r"([A-Za-z])(\d)", r"\1 \2", distinctive)
    if spaced not in variants:
        variants.append(spaced)
    joined = re.sub(r"([A-Za-z])\s+(\d)", r"\1\2", distinctive)
    if joined not in variants:
        variants.append(joined)

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

    # Split compound words: "Springhill" → "Spring Hill", "Greenfield" → "Green Field"
    # Try inserting a space at each position in long words (≥8 chars, both
    # halves ≥3 chars) to handle joined/split spelling variants.
    for word in distinctive.split():
        if len(word) < 8:
            continue
        for i in range(3, len(word) - 2):
            split_word = word[:i] + " " + word[i:]
            compound_variant = distinctive.replace(word, split_word)
            if compound_variant not in variants:
                variants.append(compound_variant)

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

        # Strategy 6: Fuzzy match — collapse doubled consonants to handle
        # Tamil transliteration variants (Alagar/Allagar, Ampar/Amppar)
        if not candidates.exists() and distinctive:
            import re as _re
            collapsed = _re.sub(r"(.)\1+", r"\1", distinctive.lower())
            if len(collapsed) >= 4:
                for school in School.objects.all().only("moe_code", "short_name"):
                    school_distinctive = _strip_prefix(school.short_name)
                    school_collapsed = _re.sub(
                        r"(.)\1+", r"\1", school_distinctive.lower()
                    )
                    if collapsed == school_collapsed:
                        candidates = School.objects.filter(
                            moe_code=school.moe_code
                        )
                        break

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

    # Auto-triage by relevance score
    if article.relevance_score and article.relevance_score >= 3:
        article.review_status = NA.APPROVED
    else:
        article.review_status = NA.REJECTED

    article.save(update_fields=[
        "relevance_score", "sentiment", "ai_summary", "mentioned_schools",
        "is_urgent", "urgent_reason", "ai_raw_response", "status",
        "review_status", "updated_at",
    ])


def reject_blocklisted(article):
    """Mark an article from a blocklisted domain as REJECTED without
    calling Gemini.

    Sprint 24 task #1a. Sets a sentinel `ai_raw_response["blocklisted_domain"]
    = True` so the reclassify_existing_articles command can identify
    blocklist-rejected rows distinct from low-relevance rejects.
    """
    from newswatch.models import NewsArticle as NA

    article.relevance_score = 1
    article.sentiment = "NEUTRAL"
    article.ai_summary = (
        "Auto-rejected: source domain is on the news-triage blocklist "
        "(classifieds / real-estate / property listings)."
    )
    article.mentioned_schools = []
    article.is_urgent = False
    article.urgent_reason = ""
    article.ai_raw_response = {"blocklisted_domain": True}
    article.status = NA.ANALYSED
    article.review_status = NA.REJECTED
    article.save(update_fields=[
        "relevance_score", "sentiment", "ai_summary", "mentioned_schools",
        "is_urgent", "urgent_reason", "ai_raw_response", "status",
        "review_status", "updated_at",
    ])


def analyse_pending_articles(batch_size=10):
    """Analyse all EXTRACTED articles that haven't been analysed yet.

    Sprint 24 task #1a: articles from DOMAIN_BLOCKLIST are short-circuited
    to REJECTED without a Gemini call.

    Args:
        batch_size: Maximum number of articles to process in one run.

    Returns:
        dict with counts: {"analysed": int, "failed": int, "skipped": int,
        "blocklisted": int}
    """
    from newswatch.models import NewsArticle as NA

    articles = NA.objects.filter(status=NA.EXTRACTED).order_by("created_at")[:batch_size]

    counts = {"analysed": 0, "failed": 0, "skipped": 0, "blocklisted": 0}

    for article in articles:
        if is_blocklisted_url(article.url):
            reject_blocklisted(article)
            counts["blocklisted"] += 1
            logger.info(
                "Article %s auto-rejected: blocklisted domain (%s)",
                article.pk, article.url,
            )
            continue

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
