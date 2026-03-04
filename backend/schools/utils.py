"""Utility functions for cleaning Malaysian school data."""

import re

# ── Title Case Configuration ─────────────────────────────────────────────

# Abbreviations that must stay UPPERCASE
_UPPER_ABBREVS = {"SJK(T)", "PPD", "PPW", "JPN", "D/A", "H/D", "YMHA"}

# Roman numerals that must stay UPPERCASE
_ROMAN_NUMERALS = {"II", "III", "IV", "V", "VI"}

# Short forms: UPPERCASE key → title-cased replacement
_SHORT_FORMS = {
    "LDG": "Ldg",
    "SG": "Sg",
    "KG": "Kg",
    "JLN": "Jln",
    "ST": "St",
}

# ── Phone Formatting Configuration ───────────────────────────────────────

# Malaysian double-digit area codes (East Malaysia + some special)
_DOUBLE_DIGIT_AREA_CODES = {"82", "83", "84", "85", "86", "87", "88", "89"}

# Single-digit area codes
_SINGLE_DIGIT_AREA_CODES = {"3", "4", "5", "6", "7", "9"}


# ── Title Case ───────────────────────────────────────────────────────────


def to_proper_case(text: str | None) -> str:
    """Convert ALL CAPS Malaysian school data to proper title case.

    Handles abbreviations (SJK(T), PPD, etc.), Roman numerals,
    short forms (LDG→Ldg), apostrophes, and parenthetical expressions.

    Args:
        text: The ALL CAPS text to convert.

    Returns:
        Properly cased string, or "" for empty/None input.
    """
    if not text:
        return ""

    # Tokenise, keeping punctuation attached to words
    # We split on whitespace but need to handle dot-joined words like KG.SIMEE
    tokens = text.split()
    result = []

    for token in tokens:
        result.append(_convert_token(token))

    return " ".join(result)


def _convert_token(token: str) -> str:
    """Convert a single token to proper case, respecting special rules."""
    upper = token.upper()

    # Check if the whole token is a known abbreviation
    if upper in _UPPER_ABBREVS:
        return upper

    # Check if it's a Roman numeral
    if upper in _ROMAN_NUMERALS:
        return upper

    # Check if it's a known short form (plain or with trailing dot)
    bare = upper.rstrip(".")
    if bare in _SHORT_FORMS:
        suffix = token[len(bare):]  # preserve trailing dot if present
        return _SHORT_FORMS[bare] + suffix

    # Handle dot-joined tokens like KG.SIMEE
    if "." in token and not token.endswith("."):
        parts = token.split(".")
        converted = [_convert_token(p) for p in parts]
        return ".".join(converted)

    # Handle parenthetical tokens like (TAMIL) or (H/D) or (KOMPLEKS
    if token.startswith("("):
        inner = token[1:]
        # Check for closing paren
        if inner.endswith(")"):
            inner_content = inner[:-1]
            # Check if inner content is an abbreviation
            if inner_content.upper() in _UPPER_ABBREVS:
                return "(" + inner_content.upper() + ")"
            return "(" + _title_word(inner_content) + ")"
        else:
            # Opening paren without close, e.g. "(KOMPLEKS"
            inner_converted = _convert_token(inner)
            return "(" + inner_converted

    # Handle closing paren, e.g. "WAWASAN)"
    if token.endswith(")"):
        inner = token[:-1]
        return _convert_token(inner) + ")"

    # Handle tokens wrapped in single quotes like 'TIMUR'
    if token.startswith("'") and token.endswith("'") and len(token) > 2:
        inner = token[1:-1]
        return "'" + _title_word(inner) + "'"

    # Handle comma-suffixed tokens like "HANGAT,"
    if token.endswith(","):
        return _convert_token(token[:-1]) + ","

    # Default: title-case the word, handling apostrophes
    return _title_word(token)


def _title_word(word: str) -> str:
    """Title-case a single word, handling apostrophes correctly.

    DATO' → Dato'
    MARY'S → Mary's
    K.PATHMANABAN → K.Pathmanaban (handled by dot-join above)
    """
    if not word:
        return word

    # Handle words with trailing apostrophe like DATO'
    if word.endswith("'") and "'" not in word[:-1]:
        return word[:-1].capitalize() + "'"

    # Handle possessives like MARY'S
    if "'" in word:
        idx = word.index("'")
        before = word[:idx].capitalize()
        after = word[idx:]  # includes the apostrophe and what follows
        return before + after.lower()

    return word.capitalize()


# ── Phone Formatting ─────────────────────────────────────────────────────


def format_phone(phone: str | None) -> str:
    """Format a Malaysian phone number to +60-X XXX XXXX format.

    Args:
        phone: Raw phone string (e.g. "049663429", "04-966 3429").

    Returns:
        Formatted string like "+60-4 966 3429", or "" for empty/None,
        or the original string if unparseable.
    """
    if not phone:
        return ""

    # Already formatted
    if phone.startswith("+60-"):
        return phone

    # Strip all non-digit characters to get raw digits
    digits = re.sub(r"\D", "", phone)

    # Must start with 0 for a Malaysian landline
    if not digits.startswith("0"):
        return phone  # unparseable

    # Remove leading 0
    digits = digits[1:]

    if not digits:
        return phone

    # Determine area code
    area_code = None
    subscriber = None

    # Try double-digit area code first
    if len(digits) >= 2 and digits[:2] in _DOUBLE_DIGIT_AREA_CODES:
        area_code = digits[:2]
        subscriber = digits[2:]
    # Try single-digit area code
    elif digits[0] in _SINGLE_DIGIT_AREA_CODES:
        area_code = digits[0]
        subscriber = digits[1:]
    else:
        return phone  # unparseable

    # Format subscriber digits
    sub_len = len(subscriber)
    if sub_len == 7:
        formatted_sub = f"{subscriber[:3]} {subscriber[3:]}"
    elif sub_len == 8:
        formatted_sub = f"{subscriber[:4]} {subscriber[4:]}"
    else:
        return phone  # unexpected length

    return f"+60-{area_code} {formatted_sub}"
