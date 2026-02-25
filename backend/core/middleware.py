"""
AuditLog middleware — sets request context (user + IP) for signal handlers.
"""

from .signals import clear_request_context, set_request_context


class AuditLogMiddleware:
    """Capture request user and IP address for AuditLog signal handlers."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user if hasattr(request, "user") and request.user.is_authenticated else None
        ip = self._get_client_ip(request)
        set_request_context(user=user, ip_address=ip)

        response = self.get_response(request)

        clear_request_context()
        return response

    def _get_client_ip(self, request):
        """Extract client IP, respecting X-Forwarded-For from Cloud Run."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")
