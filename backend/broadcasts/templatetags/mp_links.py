"""Broadcast-template helper: turn `(P### Constituency)` references in
analyst-generated prose into clickable links to the constituency page.

Example:
  "engage with their local MPs, such as YB Tuan Sanisvara Nethaji Rayer
   a/l Rajaji (P050 Jelutong) or Datuk Seri Ir. Dr. Wee Ka Siong
   (P148 Ayer Hitam), on constituency-specific school needs."

Both parenthetical spans become anchors to
`https://tamilschool.org/en/constituency/P050` etc. The MP name stays
plain text -- we don't have MP-detail pages, and the constituency page
already carries the MP contact card.

Only P-codes present in the `Constituency` table get linked -- a
hallucinated code stays as text so a broken link never reaches inboxes.
"""

import re

from django import template
from django.utils.html import escape, mark_safe

from schools.models import Constituency

register = template.Library()

# Malaysian parliamentary codes are `P` + 3 digits (P001-P222).
# Match `(P### <name>)` -- opening paren, code, whitespace, name text
# up to the closing paren. Non-greedy on the name so we stop at the
# first `)`.
_MP_PAREN_RE = re.compile(r"\((P\d{3})\s+([^)]+?)\)")


def _valid_codes() -> set:
    return set(Constituency.objects.values_list("code", flat=True))


@register.filter(name="linkify_mps")
def linkify_mps(text, locale: str = "en"):
    """Escape `text`, wrap valid `(P### Name)` spans in <a>, return safe HTML.

    Usage:  {{ analysis.executive_summary|linkify_mps }}

    Pass a locale to route the link through the right i18n prefix:
      {{ analysis.executive_summary|linkify_mps:"ta" }}
    """
    if not text:
        return text

    escaped = escape(str(text))
    codes = _valid_codes()

    def _sub(match: "re.Match") -> str:
        code = match.group(1)
        name = match.group(2)
        if code not in codes:
            return match.group(0)
        url = f"https://tamilschool.org/{locale}/constituency/{code}"
        return (
            f'(<a href="{url}" '
            f'style="color: #2563eb; text-decoration: none;">'
            f"{code} {name}</a>)"
        )

    return mark_safe(_MP_PAREN_RE.sub(_sub, escaped))
