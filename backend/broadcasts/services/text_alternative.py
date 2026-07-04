"""Convert broadcast HTML into a clean plain-text alternative body.

Audit 2026-07-01: `strip_tags(html_content)` was being used everywhere.
Django's `strip_tags` removes the tag delimiters but leaves the text
CONTENTS of `<style>` and `<script>` blocks in place — the plain-text
`textContent` sent to Brevo ended up full of raw CSS rules ("body {
font-family: ...; }"). That's a well-known spam-scoring hit.

This helper strips `<style>` and `<script>` bodies before falling back
to `strip_tags`, then collapses runs of whitespace and blank lines so
the output is readable in a plain-text mail client.

Not a full Markdown rendering — the goal is a Gmail-happy fallback, not
a pretty text-only newsletter. If a template ever needs richer text
output, add a dedicated `.txt` sibling template and render both.
"""

import re

from django.utils.html import strip_tags

_STYLE_BLOCK_RE = re.compile(
    r"<style\b[^>]*>.*?</style>", re.IGNORECASE | re.DOTALL
)
_SCRIPT_BLOCK_RE = re.compile(
    r"<script\b[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL
)
_HEAD_BLOCK_RE = re.compile(
    r"<head\b[^>]*>.*?</head>", re.IGNORECASE | re.DOTALL
)
_WHITESPACE_RUNS_RE = re.compile(r"[ \t]+")
_BLANK_LINE_RUNS_RE = re.compile(r"\n\s*\n\s*\n+")


def html_to_text_alternative(html: str) -> str:
    """Return a plain-text version of a broadcast HTML body."""
    if not html:
        return ""
    # Strip the whole <head> (dodges <title>, <meta>, and any style there).
    text = _HEAD_BLOCK_RE.sub("", html)
    # Belt-and-braces: strip block-level style/script elsewhere too.
    text = _STYLE_BLOCK_RE.sub("", text)
    text = _SCRIPT_BLOCK_RE.sub("", text)
    text = strip_tags(text)
    # Collapse whitespace runs, then squeeze consecutive blank lines
    # so the output isn't a wall of empty rows from removed block tags.
    text = _WHITESPACE_RUNS_RE.sub(" ", text)
    text = _BLANK_LINE_RUNS_RE.sub("\n\n", text)
    return text.strip()
