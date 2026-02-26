"""Template tags for highlighting keywords in Hansard text."""

import re

from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# Keywords to highlight — matches SJK(T) variants and Tamil school references
_HIGHLIGHT_PATTERNS = [
    r"SJK\s*\(T\)",
    r"SJKT",
    r"S\.J\.K\.\s*\(T\)",
    r"S\.J\.K\s*\(T\)",
    r"sekolah\s+jenis\s+kebangsaan\s+(?:\(tamil\)|tamil)",
    r"sekolah\s+tamil",
]

_HIGHLIGHT_RE = re.compile(
    "|".join(_HIGHLIGHT_PATTERNS), re.IGNORECASE
)


@register.filter(name="highlight_keywords")
def highlight_keywords(text):
    """Wrap Tamil school keyword matches in <mark> tags.

    Usage: {{ mention.verbatim_quote|highlight_keywords }}
    """
    if not text:
        return ""

    def _replacer(match):
        return f"<mark>{match.group(0)}</mark>"

    result = _HIGHLIGHT_RE.sub(_replacer, str(text))
    return mark_safe(result)
