"""Permission classes specific to the community / photo workflow.

`IsPhotoApprover` deliberately excludes MODERATOR — Sprint 14 design says
photos are approved only by SUPERADMIN or the school's bound admin. See
docs/plans/2026-04-22-image-library-sprint-plan.md Decision #5.
"""

from rest_framework.permissions import BasePermission


class IsPhotoApprover(BasePermission):
    """SUPERADMIN OR the bound admin of the suggestion's school.

    MODERATOR is intentionally NOT granted approval rights for photos —
    photo decisions are scoped to the school in question.

    Must be used after IsProfileAuthenticated. Accepts either:
      - A Suggestion (uses .school_id)
      - A SchoolImage (uses .school_id)
      - A School (uses .pk / .moe_code)
    """

    def has_object_permission(self, request, view, obj):
        profile = getattr(request, "user_profile", None)
        if not profile:
            return False
        if profile.role == "SUPERADMIN":
            return True
        # School.pk == moe_code (string); admin_school_id is FK to that PK.
        target_school_id = getattr(obj, "school_id", None) or getattr(obj, "pk", None)
        return bool(profile.admin_school_id and profile.admin_school_id == target_school_id)
