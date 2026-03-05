"""Search normalised Hansard text for Tamil school keyword matches.

For each match, extracts:
- The verbatim quote (the original sentence/line containing the keyword)
- Context before (includes speaker identification if found)
- Context after (~500 chars)
- Speaker name extracted from Hansard formatting
- Page number where the match was found
"""

import logging
import re

from .normalizer import normalize_text

logger = logging.getLogger(__name__)

CONTEXT_CHARS = 500

# Pattern to find Malaysian Hansard speaker identifications.
# Matches patterns like:
#   "Tuan Ganabatirau a/l Veraman [Klang]:"
#   "Dato' Sri Hajah Nancy binti Shukri:"
#   "Timbalan Menteri Pendidikan [Tuan Wong Kah Woh]:"
#   "Tuan Yang di-Pertua:"
# The speaker line usually starts with a title and ends with a colon.
SPEAKER_PATTERN = re.compile(
    r'(?:^|\n)\s*'  # Start of line
    r'('
    r'(?:YAB|Y\.?A\.?B\.?'
    r'|Tuan|Puan|Dato\'?|Datuk|Tan Sri|Tun|Dr\.'
    r'|Y\.?B\.?|Yang Berhormat'
    r'|Timbalan (?:Menteri|Yang di-Pertua)'
    r'|Menteri(?:\s+Besar)?'
    r'|Setiausaha Parlimen'
    r'|Tuan Yang di-Pertua)'
    r'[^:\n]{2,120}'  # Name + optional [constituency], 2-120 chars
    r')'
    r'\s*:',  # Colon marks end of speaker identification
    re.IGNORECASE,
)


def search_keywords(
    pages: list[tuple[int, str]],
    keywords: list[str],
) -> list[dict]:
    """Search through extracted pages for keyword matches.

    Args:
        pages: List of (page_number, raw_text) tuples from the extractor.
        keywords: List of keywords to search for (already normalised/lowercase).

    Returns:
        List of match dicts with keys:
        - page_number: int
        - keyword_matched: str
        - verbatim_quote: str (the original sentence containing the match)
        - context_before: str (up to speaker identification or ~500 chars)
        - context_after: str (~500 chars after the match)
        - match_position: int (character offset in normalised page text)
        - speaker_name: str (extracted from Hansard format, or "")
        - speaker_constituency: str (extracted from [Constituency], or "")
    """
    matches = []
    # Deduplicate exact same keyword at the exact same position on a page
    seen_positions = set()

    # Build a combined page lookup for cross-page speaker detection
    page_texts = {page_num: raw_text for page_num, raw_text in pages}
    page_nums = [page_num for page_num, _ in pages]

    for page_num, raw_text in pages:
        if not raw_text or not raw_text.strip():
            continue

        normalised = normalize_text(raw_text)

        for keyword in keywords:
            kw_lower = keyword.lower()

            # Find all occurrences of this keyword in the normalised text
            start = 0
            while True:
                pos = normalised.find(kw_lower, start)
                if pos == -1:
                    break

                # Deduplicate: same keyword at the exact same position
                dedup_key = (page_num, pos, kw_lower)
                if dedup_key in seen_positions:
                    start = pos + 1
                    continue
                seen_positions.add(dedup_key)

                # Extract verbatim quote from the ORIGINAL text
                verbatim = _extract_verbatim(raw_text, normalised, pos, kw_lower)

                # Extract context from the ORIGINAL text
                ctx_before, ctx_after = _extract_context(
                    raw_text, normalised, pos, kw_lower
                )

                # Find the speaker — search backwards through current page
                # and previous page if needed
                speaker_name, speaker_constituency = _find_speaker(
                    raw_text, normalised, pos, page_num, page_texts, page_nums
                )

                matches.append({
                    "page_number": page_num,
                    "keyword_matched": keyword,
                    "verbatim_quote": verbatim,
                    "context_before": ctx_before,
                    "context_after": ctx_after,
                    "match_position": pos,
                    "speaker_name": speaker_name,
                    "speaker_constituency": speaker_constituency,
                })

                start = pos + len(kw_lower)

    logger.info("Found %d keyword matches across %d pages", len(matches), len(pages))
    return matches


def _find_speaker(
    raw_text: str,
    normalised: str,
    match_pos: int,
    page_num: int,
    page_texts: dict[int, str],
    page_nums: list[int],
) -> tuple[str, str]:
    """Find the speaker by searching backwards for a Hansard speaker pattern.

    Looks through the current page text before the keyword match. If no
    speaker is found, searches the previous page's text as well (speakers
    often start on one page and their speech continues to the next).

    Returns:
        (speaker_name, constituency) — empty strings if not found.
    """
    # Map normalised position to approximate raw text position
    ratio = len(raw_text) / len(normalised) if normalised else 1
    raw_pos = min(len(raw_text), int(match_pos * ratio))

    # Search current page text BEFORE the match
    text_before_match = raw_text[:raw_pos]
    speaker, constituency = _extract_last_speaker(text_before_match)

    if speaker:
        return speaker, constituency

    # If not found, try previous page
    try:
        page_idx = page_nums.index(page_num)
    except ValueError:
        return "", ""

    for lookback in range(1, 3):  # 1 and 2 pages back
        prev_idx = page_idx - lookback
        if prev_idx < 0:
            break
        prev_page_num = page_nums[prev_idx]
        prev_text = page_texts.get(prev_page_num, "")
        if prev_text:
            speaker, constituency = _extract_last_speaker(prev_text)
            if speaker:
                return speaker, constituency

    return "", ""


def _extract_last_speaker(text: str) -> tuple[str, str]:
    """Find the last speaker identification pattern in the given text.

    Returns (speaker_name, constituency) or ("", "").
    """
    all_matches = list(SPEAKER_PATTERN.finditer(text))
    if not all_matches:
        return "", ""

    # Take the LAST match (closest to our keyword)
    last = all_matches[-1]
    raw_speaker = last.group(1).strip()

    # Extract constituency from [Constituency] if present
    constituency = ""
    constituency_match = re.search(r'\[([^\]]+)\]', raw_speaker)
    if constituency_match:
        constituency = constituency_match.group(1).strip()

    # Clean the speaker name
    name = _clean_speaker_name(raw_speaker)

    return name, constituency


def _clean_speaker_name(raw: str) -> str:
    """Clean a raw Hansard speaker identification into a usable name.

    Input examples:
        "Tuan Ganabatirau a/l Veraman [Klang]"
        "Dato' Sri Hajah Nancy binti Shukri"
        "Timbalan Menteri Pendidikan [Tuan Wong Kah Woh]"
        "Tuan Yang di-Pertua"

    Returns the cleaned name.
    """
    name = raw.strip()

    # Remove constituency bracket: "Name [Klang]" → "Name"
    name = re.sub(r'\s*\[[^\]]+\]\s*', ' ', name).strip()

    # Skip generic titles that aren't personal names
    generic_titles = [
        "tuan yang di-pertua",
        "timbalan yang di-pertua",
        "tuan pengerusi",
        "puan pengerusi",
    ]
    if name.lower() in generic_titles:
        return ""

    # For "Timbalan Menteri Pendidikan [Tuan Wong Kah Woh]",
    # the actual name is in the brackets — already extracted above,
    # but if the outer name is a role title, try to get the inner name
    inner_match = re.search(r'\[([^\]]+)\]', raw)
    if inner_match:
        lower = name.lower()
        if any(lower.startswith(t) for t in [
            "yab", "menteri", "timbalan menteri", "setiausaha parlimen",
        ]):
            name = inner_match.group(1).strip()

    # Remove common titles/honorifics prefix for cleaner name
    # but keep the full name for display
    # Don't strip "Tuan/Puan" etc. — keep the name as-is from Hansard

    return name


def _extract_verbatim(
    raw_text: str, normalised: str, match_pos: int, keyword: str
) -> str:
    """Extract the sentence or line containing the keyword match.

    Uses the normalised text for position finding, then maps back
    to the raw text for the verbatim quote.
    """
    # Find sentence boundaries in normalised text (period, newline, or ±200 chars)
    sent_start = match_pos
    sent_end = match_pos + len(keyword)

    # Walk backwards to find sentence start
    lookback = max(0, match_pos - 200)
    for delim in [". ", "\n", ".\n"]:
        last_delim = normalised.rfind(delim, lookback, match_pos)
        if last_delim != -1:
            sent_start = last_delim + len(delim)
            break
    else:
        sent_start = lookback

    # Walk forwards to find sentence end
    lookahead = min(len(normalised), match_pos + len(keyword) + 200)
    for delim in [". ", "\n", ".\n"]:
        next_delim = normalised.find(delim, match_pos + len(keyword), lookahead)
        if next_delim != -1:
            sent_end = next_delim + 1
            break
    else:
        sent_end = lookahead

    # Map positions back to raw text (best effort — normalisation may shift positions)
    # Since normalisation only lowercases and collapses whitespace, positions are close
    ratio = len(raw_text) / len(normalised) if normalised else 1
    raw_start = max(0, int(sent_start * ratio))
    raw_end = min(len(raw_text), int(sent_end * ratio))

    return raw_text[raw_start:raw_end].strip()


def _extract_context(
    raw_text: str, normalised: str, match_pos: int, keyword: str
) -> tuple[str, str]:
    """Extract context around the match.

    For context_before: extends to include the speaker identification if
    found within 3000 chars, otherwise falls back to 500 chars.
    For context_after: ~500 chars.

    Returns (context_before, context_after) from the raw text.
    """
    ratio = len(raw_text) / len(normalised) if normalised else 1

    # Map match position to raw text
    raw_match_start = max(0, int(match_pos * ratio))
    raw_match_end = min(len(raw_text), int((match_pos + len(keyword)) * ratio))

    # Context before — try to include speaker identification
    # First, look for a speaker pattern in a wider window (up to 3000 chars)
    wide_start = max(0, raw_match_start - 3000)
    wide_before = raw_text[wide_start:raw_match_start]
    speaker_matches = list(SPEAKER_PATTERN.finditer(wide_before))

    if speaker_matches:
        # Include from the last speaker identification
        last_speaker_pos = speaker_matches[-1].start()
        ctx_start = wide_start + last_speaker_pos
    else:
        # Fallback: just use CONTEXT_CHARS
        ctx_start = max(0, raw_match_start - CONTEXT_CHARS)

    context_before = raw_text[ctx_start:raw_match_start].strip()

    # Context after — standard 500 chars
    ctx_end = min(len(raw_text), raw_match_end + CONTEXT_CHARS)
    context_after = raw_text[raw_match_end:ctx_end].strip()

    return context_before, context_after
