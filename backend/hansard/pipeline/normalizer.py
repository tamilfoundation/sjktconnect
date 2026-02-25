"""Text normalisation for Hansard content before keyword search.

MPs use inconsistent forms when referring to Tamil schools:
- "SJK(T)", "SJKT", "S.J.K.(T)", "S.J.K(T)"
- "Sekolah Tamil", "Sekolah Jenis Kebangsaan Tamil"
- Various spacing and casing

The normaliser standardises text so that a single keyword list
catches all variants.
"""

import re
import unicodedata


def normalize_text(raw: str) -> str:
    """Normalise raw Hansard text for keyword matching.

    Steps:
    1. Unicode NFKC normalisation (fixes non-breaking spaces, etc.)
    2. Lowercase
    3. Collapse whitespace (newlines, tabs, multiple spaces → single space)
    4. Normalise SJK(T) variants → canonical "sjk(t)"
    5. Strip leading/trailing whitespace

    Args:
        raw: Raw text extracted from PDF.

    Returns:
        Normalised text ready for keyword search.
    """
    if not raw:
        return ""

    # Step 1: Unicode normalisation — handles non-breaking spaces, ligatures
    text = unicodedata.normalize("NFKC", raw)

    # Step 2: Lowercase
    text = text.lower()

    # Step 3: Collapse whitespace
    text = re.sub(r"\s+", " ", text)

    # Step 4: Normalise SJK(T) variants
    # "s.j.k.(t)" or "s.j.k(t)" → "sjk(t)"
    text = re.sub(r"s\.j\.k\.?\s*\(t\)", "sjk(t)", text)
    # "sjkt" (no brackets) → "sjk(t)"
    # Use word boundary to avoid matching inside longer words
    text = re.sub(r"\bsjkt\b", "sjk(t)", text)

    # Step 5: Strip
    text = text.strip()

    return text
