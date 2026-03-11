from django.db import transaction

from community.models import Suggestion
from outreach.models import SchoolImage


def approve_suggestion(suggestion, reviewer):
    """Approve a suggestion: apply changes, award points."""
    with transaction.atomic():
        suggestion.status = Suggestion.Status.APPROVED
        suggestion.reviewed_by = reviewer

        # Award points (not for own school)
        if suggestion.user.admin_school_id != suggestion.school_id:
            points = Suggestion.POINTS_MAP.get(suggestion.type, 0)
            suggestion.points_awarded = points
            suggestion.user.points += points
            suggestion.user.save(update_fields=["points"])

        # Apply the change
        if suggestion.type == Suggestion.Type.DATA_CORRECTION:
            _apply_data_correction(suggestion)
        elif suggestion.type == Suggestion.Type.PHOTO_UPLOAD:
            _apply_photo_upload(suggestion)
        # NOTE type: no auto-apply, moderator acts manually

        suggestion.save()
    return suggestion


def reject_suggestion(suggestion, reviewer, reason=""):
    suggestion.status = Suggestion.Status.REJECTED
    suggestion.reviewed_by = reviewer
    suggestion.review_note = reason
    suggestion.save()
    return suggestion


def _apply_data_correction(suggestion):
    """Update the school field with the suggested value."""
    school = suggestion.school
    field = suggestion.field_name
    if field.startswith("leadership_"):
        return
    if field in Suggestion.SUGGESTIBLE_FIELDS and hasattr(school, field):
        setattr(school, field, suggestion.suggested_value)
        school.save(update_fields=[field, "updated_at"])


def _apply_photo_upload(suggestion):
    """Create a SchoolImage from the suggestion's image bytes."""
    if not suggestion.image:
        return
    existing_count = SchoolImage.objects.filter(school=suggestion.school).count()
    if existing_count >= 10:
        return
    max_position = (
        SchoolImage.objects.filter(school=suggestion.school)
        .order_by("-position")
        .values_list("position", flat=True)
        .first()
    ) or 0
    SchoolImage.objects.create(
        school=suggestion.school,
        image_url=f"/api/v1/suggestions/{suggestion.pk}/image/",
        source="COMMUNITY",
        position=max_position + 1,
        uploaded_by=suggestion.user,
    )
