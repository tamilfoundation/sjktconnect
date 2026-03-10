"""DRF permission classes for Magic Link session authentication."""

from rest_framework.permissions import BasePermission

from accounts.models import SchoolContact


class IsMagicLinkAuthenticated(BasePermission):
    """Allows access only to users with a valid Magic Link session.

    Checks request.session for school_contact_id and verifies the
    SchoolContact record exists and is active.

    Sets request.school_contact and request.school_moe_code on success.
    """

    message = "You must be logged in via a magic link to perform this action."

    def has_permission(self, request, view):
        contact_id = request.session.get("school_contact_id")
        if not contact_id:
            return False

        try:
            contact = SchoolContact.objects.select_related("school").get(
                id=contact_id, is_active=True
            )
        except SchoolContact.DoesNotExist:
            return False

        # Attach to request for downstream use
        request.school_contact = contact
        request.school_moe_code = contact.school.moe_code
        return True


# --- Community Admin permission classes (Sprint CA-1) ---

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
        # Determine the school from the object
        from schools.models import School
        if isinstance(obj, School):
            school = obj
        elif hasattr(obj, "school"):
            school = obj.school
        else:
            return False
        return profile.admin_school_id == school.pk
