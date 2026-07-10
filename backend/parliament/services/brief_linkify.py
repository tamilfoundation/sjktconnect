"""Hyperlink mentioned-school names inside a SittingBrief's HTML.

After a brief is generated, every school linked to the sitting's mentions
(via ``MentionedSchool``) has its name wrapped in an ``<a>`` pointing at
its canonical school page — so the parliamentary report is navigable to
and from each school. This makes the Details / Verbatim sections clickable.

The brief HTML is simple (h2 / p / blockquote, no existing anchors), so a
longest-phrase-first, placeholder-guarded replace is safe: matched spans
become opaque tokens that later regexes can't re-match, preventing nested
or double links.
"""

import re

from hansard.models import MentionedSchool
from schools.services.revalidation import build_school_slug

# Leading SJK(T) / Sekolah Jenis Kebangsaan (Tamil) prefix — stripped to
# get a school's distinctive core (e.g. "Ladang Seafield").
_PREFIX = re.compile(
    r"^\s*(?:sjk\s*\(?\s*t\s*\)?|sjkt|s\.j\.k\.?\s*\(?t\)?"
    r"|sekolah\s+jenis\s+kebangsaan\s*\(?\s*tamil\s*\)?)\s+",
    re.IGNORECASE,
)
# Optional prefix in the display text, so we link the whole "SJK(T) X" span.
_DISPLAY_PREFIX = r"(?:SJK\s*\(?\s*T\s*\)?\s+|SJKT\s+|Sekolah\s+Jenis\s+Kebangsaan\s*\(?\s*Tamil\s*\)?\s+)?"


def _core(name):
    return _PREFIX.sub("", (name or "").strip()).strip()


def _expand_ldg(s):
    return re.sub(r"\bldg\.?\s+", "ladang ", s, flags=re.IGNORECASE)


def linkify_schools(html, sitting):
    """Return ``html`` with mentioned-school names linked to school pages."""
    if not html:
        return html
    # Idempotency: never re-link already-linked HTML (would nest anchors).
    if "tamilschool.org/en/school/" in html:
        return html

    phrase_url = {}  # lowercased distinctive phrase -> canonical url
    rows = (MentionedSchool.objects
            .filter(mention__sitting=sitting)
            .select_related("school"))
    for ms in rows:
        sc = ms.school
        slug = build_school_slug(sc.moe_code, sc.short_name or "", getattr(sc, "city", "") or "")
        url = f"https://tamilschool.org/en/school/{slug}"
        # Prefer the text the matcher actually found; also try the short name.
        for raw in filter(None, {_core(ms.matched_text), _core(sc.short_name)}):
            for form in {raw, _expand_ldg(raw)}:
                form = form.strip().lower()
                if len(form) >= 5:  # avoid tiny ambiguous fragments
                    phrase_url.setdefault(form, url)

    if not phrase_url:
        return html

    placeholders = {}
    out = html
    # Longest phrases first so "ladang seafield" wins over any substring.
    for phrase in sorted(phrase_url, key=len, reverse=True):
        url = phrase_url[phrase]
        pat = re.compile(_DISPLAY_PREFIX + "(?:" + re.escape(phrase) + ")", re.IGNORECASE)

        def repl(mo, url=url):
            token = f"\x00L{len(placeholders)}\x00"
            placeholders[token] = f'<a href="{url}">{mo.group(0)}</a>'
            return token

        out = pat.sub(repl, out)

    for token, anchor in placeholders.items():
        out = out.replace(token, anchor)
    return out
