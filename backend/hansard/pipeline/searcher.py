"""Search normalised Hansard text for Tamil school keyword matches.

For each match, extracts:
- The verbatim quote (the original sentence/line containing the keyword)
- Context before (~500 chars)
- Context after (~500 chars)
- Page number where the match was found
"""

import logging

from .normalizer import normalize_text

logger = logging.getLogger(__name__)

CONTEXT_CHARS = 500


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
        - context_before: str (~500 chars before the match)
        - context_after: str (~500 chars after the match)
        - match_position: int (character offset in normalised page text)
    """
    matches = []
    # Deduplicate exact same keyword at the exact same position on a page
    seen_positions = set()

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

                matches.append({
                    "page_number": page_num,
                    "keyword_matched": keyword,
                    "verbatim_quote": verbatim,
                    "context_before": ctx_before,
                    "context_after": ctx_after,
                    "match_position": pos,
                })

                start = pos + len(kw_lower)

    logger.info("Found %d keyword matches across %d pages", len(matches), len(pages))
    return matches


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
    """Extract ±500 chars of context around the match.

    Returns (context_before, context_after) from the raw text.
    """
    ratio = len(raw_text) / len(normalised) if normalised else 1

    # Map match position to raw text
    raw_match_start = max(0, int(match_pos * ratio))
    raw_match_end = min(len(raw_text), int((match_pos + len(keyword)) * ratio))

    # Context before
    ctx_start = max(0, raw_match_start - CONTEXT_CHARS)
    context_before = raw_text[ctx_start:raw_match_start].strip()

    # Context after
    ctx_end = min(len(raw_text), raw_match_end + CONTEXT_CHARS)
    context_after = raw_text[raw_match_end:ctx_end].strip()

    return context_before, context_after
