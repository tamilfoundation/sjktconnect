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
