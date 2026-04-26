"""Rate limits for photo uploads (Sprint 14).

Limits per Image Library plan: 5 uploads / user / day, 20 / school / day.
Both limits must pass for the upload to proceed; whichever is exhausted
first surfaces a 429 with a Retry-After header (DRF default behaviour).
"""

from rest_framework.throttling import SimpleRateThrottle


class PhotoUploadUserThrottle(SimpleRateThrottle):
    """5 photo uploads per user per day."""

    scope = "photo_upload_user"

    def get_cache_key(self, request, view):
        profile = getattr(request, "user_profile", None)
        if not profile:
            return None
        return self.cache_format % {
            "scope": self.scope,
            "ident": f"u{profile.pk}",
        }


class PhotoUploadSchoolThrottle(SimpleRateThrottle):
    """20 photo uploads per school per day (across all uploaders)."""

    scope = "photo_upload_school"

    def get_cache_key(self, request, view):
        moe_code = view.kwargs.get("moe_code")
        if not moe_code:
            return None
        return self.cache_format % {
            "scope": self.scope,
            "ident": f"s{moe_code}",
        }
