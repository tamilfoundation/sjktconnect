"""Rate limits for donation-status polling (audit 2026-07-01).

The Toyyib return-URL loops back to a thank-you page that polls
`/api/v1/donations/status/<uuid>/` for confirmation. 30/hour/IP is
generous for a real donor's tab-refresh pattern but keeps a scraper
or a bugged FE loop bounded.
"""

from rest_framework.throttling import SimpleRateThrottle


class DonationStatusThrottle(SimpleRateThrottle):
    scope = "donation_status"

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }
