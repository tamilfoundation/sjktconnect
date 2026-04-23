"""DRF permission classes for community UserProfile session authentication.

Magic-link permission (IsMagicLinkAuthenticated) removed in Sprint 11 Phase 3;
see docs/tech-debt.md TD-02.
"""

from rest_framework.permissions import BasePermission

from accounts.models import UserProfile


class IsProfileAuthenticated(BasePermission):
    """Check that the request has a valid UserProfile session."""

    def has_permission(self, request, view):
        profile_id = request.session.get("user_profile_id")
        if not profile_id:
            return False
        try:
            profile = UserProfile.objects.select_related(
                "admin_school",
            ).get(id=profile_id, is_active=True)
            request.user_profile = profile
            return True
        except UserProfile.DoesNotExist:
            return False


class IsModeratorOrAbove(BasePermission):
    """Requires MODERATOR or SUPERADMIN role. Must be used after IsProfileAuthenticated."""

    def has_permission(self, request, view):
        profile = getattr(request, "user_profile", None)
        if not profile:
            return False
        return profile.role in ("MODERATOR", "SUPERADMIN")


class IsSuperAdmin(BasePermission):
    """Requires SUPERADMIN role. Must be used after IsProfileAuthenticated."""

    def has_permission(self, request, view):
        profile = getattr(request, "user_profile", None)
        if not profile:
            return False
        return profile.role == "SUPERADMIN"


class IsSchoolAdminForObject(BasePermission):
    """Check user is admin for the specific school object.

    Works with objects that ARE a School or have a .school FK.
    Must be used after IsProfileAuthenticated.
    """

    def has_object_permission(self, request, view, obj):
        profile = getattr(request, "user_profile", None)
        if not profile or not profile.admin_school_id:
            return False
        # Superadmin can access any school
        if profile.role == "SUPERADMIN":
            return True
        from schools.models import School
        if isinstance(obj, School):
            school = obj
        elif hasattr(obj, "school"):
            school = obj.school
        else:
            return False
        return profile.admin_school_id == school.pk
