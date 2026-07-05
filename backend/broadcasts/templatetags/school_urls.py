"""Broadcast-template helper: canonical school URL for a `School` row.

Reuses `schools.services.revalidation.build_school_slug` (which mirrors
`frontend/lib/urls.ts::schoolPath`) so an email link resolves directly to
the SEO-slug URL instead of the legacy /school/<moe_code> path that
now 301-redirects.

Audit 2026-07-05: monthly blast school links were using the bare-code
form, causing every click to hop through a redirect.
"""

from django import template

from schools.services.revalidation import build_school_slug

register = template.Library()


@register.simple_tag
def school_url(school, locale: str = "en") -> str:
    """Return the fully-qualified canonical school URL for `school`.

    Usage:  {% school_url s %}  or  {% school_url s "ta" %}
    """
    slug = build_school_slug(
        school.moe_code,
        getattr(school, "short_name", "") or "",
        getattr(school, "city", "") or "",
    )
    return f"https://tamilschool.org/{locale}/school/{slug}"
