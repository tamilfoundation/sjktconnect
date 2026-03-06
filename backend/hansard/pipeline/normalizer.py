"""Text normalisation for Hansard content.

Two functions:
- normalize_text(): for keyword matching (lowercase, collapse whitespace,
  normalise SJK(T) variants)
- clean_extracted_text(): for stored quotes/context (fix PDF artefacts
  while preserving original casing and formatting)
"""

import re
import unicodedata


def clean_extracted_text(text: str) -> str:
    """Clean PDF extraction artefacts from verbatim quotes and context.

    Fixes common pdfplumber issues without changing the text's meaning:
    - Double/triple periods with spaces (". ." → ".")
    - Garbled short fragments at paragraph starts (e.g. "ohoh")
    - Excessive whitespace
    - Orphaned punctuation
    """
    if not text:
        return ""

    # Unicode normalisation
    text = unicodedata.normalize("NFKC", text)

    # Fix double/triple periods: ". ." or ".  ." → "."
    text = re.sub(r"\.\s*\.\s*\.?", ".", text)

    # Fix orphaned punctuation with space before it: " ," → ","
    text = re.sub(r"\s+([,;:])", r"\1", text)

    # Remove short garbled fragments at the very start of text
    # (2-5 lowercase chars followed by a space and then an uppercase letter)
    text = re.sub(r"^[a-z]{2,5}\s+(?=[A-Z])", "", text)

    # Collapse multiple spaces
    text = re.sub(r"  +", " ", text)

    return text.strip()


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
