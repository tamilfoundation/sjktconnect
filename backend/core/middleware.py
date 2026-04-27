"""
Cross-cutting Django middleware:
  * AuditLogMiddleware — sets request context (user + IP) for signal handlers.
  * IPBlockMiddleware — short-circuits known scraper IPs with 403 to stop
    egress drain. Sprint 17 (Egress Hardening) discovered the Egress-Fix
    sprint had claimed this work but never actually landed it.
"""

from django.http import HttpResponseForbidden

from .signals import clear_request_context, set_request_context


# Known abusive scrapers — verified via Cloud Run access logs as generating
# disproportionate traffic with fake/outdated user agents and ignoring
# robots.txt. Add IPs here as they're confirmed (don't speculate; verify
# with `gcloud logging read` first or you'll block real users).
BLOCKED_IPS = frozenset({
    # 88.216.210.27 — Chrome/91 fake-UA scraper hitting every school +
    # constituency + DUN page systematically (~1,400 req/day at the time
    # of Sprint 17 investigation 2026-04-27). Originally flagged in
    # docs/egress-investigation-report.md.
    "88.216.210.27",
})


def _get_client_ip(request) -> str | None:
    """Resolve the real client IP behind Cloudflare and Cloud Run proxies.

    Priority: Cloudflare's CF-Connecting-IP > X-Forwarded-For first hop >
    REMOTE_ADDR (direct connection — Cloud Run service URL without proxy).
    """
    cf = request.META.get("HTTP_CF_CONNECTING_IP")
    if cf:
        return cf.strip()
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class IPBlockMiddleware:
    """Return 403 immediately for IPs on the BLOCKED_IPS list.

    Placed early in the MIDDLEWARE chain so the request never reaches
    URL routing, view dispatch, DB queries, or serializers. Cheapest
    possible way to stop a scraper from generating egress.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        client_ip = _get_client_ip(request)
        if client_ip in BLOCKED_IPS:
            return HttpResponseForbidden(b"")
        return self.get_response(request)


class AuditLogMiddleware:
    """Capture request user and IP address for AuditLog signal handlers."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user if hasattr(request, "user") and request.user.is_authenticated else None
        ip = _get_client_ip(request)
        set_request_context(user=user, ip_address=ip)

        response = self.get_response(request)

        clear_request_context()
        return response

    def _get_client_ip(self, request):
        """Backwards-compat alias — old call sites may still reach for this."""
        return _get_client_ip(request)
