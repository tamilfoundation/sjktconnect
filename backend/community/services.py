import logging

from django.core.files.base import ContentFile
from django.db import transaction

from community.models import Suggestion
from outreach.models import SchoolImage

logger = logging.getLogger(__name__)


def approve_suggestion(suggestion, reviewer):
    """Approve a suggestion: apply changes, award points.

    Caller is responsible for cap enforcement (the API view rejects PHOTO_UPLOAD
    approvals with 409 when the school is at the 20-photo cap before reaching
    here). This function will silently no-op if the cap is hit at the
    transaction boundary as a defence in depth.
    """
    with transaction.atomic():
        suggestion.status = Suggestion.Status.APPROVED
        suggestion.reviewed_by = reviewer

        if suggestion.user.admin_school_id != suggestion.school_id:
            points = Suggestion.POINTS_MAP.get(suggestion.type, 0)
            suggestion.points_awarded = points
            suggestion.user.points += points
            suggestion.user.save(update_fields=["points"])

        if suggestion.type == Suggestion.Type.DATA_CORRECTION:
            _apply_data_correction(suggestion)
        elif suggestion.type == Suggestion.Type.PHOTO_UPLOAD:
            _apply_photo_upload(suggestion)

        suggestion.save()
    return suggestion


def reject_suggestion(suggestion, reviewer, reason=""):
    """Reject a suggestion. Photos: delete the staged file from Storage."""
    with transaction.atomic():
        suggestion.status = Suggestion.Status.REJECTED
        suggestion.reviewed_by = reviewer
        suggestion.review_note = reason
        if suggestion.type == Suggestion.Type.PHOTO_UPLOAD and suggestion.pending_image:
            # delete=False keeps the field clear without saving twice; we save
            # the suggestion below.
            try:
                suggestion.pending_image.delete(save=False)
            except Exception:  # noqa: BLE001
                # Storage delete is best-effort. Log so the janitor (Sprint 33
                # weekly cron `janitor_orphan_images`) has a signal to sweep.
                logger.exception(
                    "reject_suggestion: failed to delete pending image %s "
                    "for suggestion %s — janitor will retry",
                    suggestion.pending_image.name, suggestion.pk,
                )
        suggestion.save()
    return suggestion


def _apply_data_correction(suggestion):
    """Update the school field with the suggested value.

    Audit 2026-07-01: removed a `leadership_` prefix guard here — the
    leadership-suggestion flow was retired when SchoolLeader got its
    own CRUD endpoints (Sprint 20), and no field in SUGGESTIBLE_FIELDS
    starts with "leadership_" anyway.
    """
    school = suggestion.school
    field = suggestion.field_name
    if field in Suggestion.SUGGESTIBLE_FIELDS and hasattr(school, field):
        setattr(school, field, suggestion.suggested_value)
        school.save(update_fields=[field, "updated_at"])


PHOTO_CAP_PER_SCHOOL = 20


def _apply_photo_upload(suggestion):
    """Move pending bytes into a SchoolImage row.

    Reads the bytes from the staged Suggestion.pending_image and writes them
    into a fresh SchoolImage.image_file (different storage path, lives under
    schools/<moe>/). Then clears the pending file. If the school is at cap,
    the suggestion is still marked APPROVED but no SchoolImage is created —
    this matches the legacy behaviour. Cap should be enforced upstream by
    the API view.
    """
    if not suggestion.pending_image:
        return
    existing_count = SchoolImage.objects.filter(school=suggestion.school).count()
    if existing_count >= PHOTO_CAP_PER_SCHOOL:
        return

    max_position = (
        SchoolImage.objects.filter(school=suggestion.school)
        .order_by("-position")
        .values_list("position", flat=True)
        .first()
    ) or 0

    src = suggestion.pending_image
    src.open("rb")
    try:
        data = src.read()
    finally:
        src.close()

    name = src.name.rsplit("/", 1)[-1]
    image = SchoolImage(
        school=suggestion.school,
        source=SchoolImage.Source.COMMUNITY,
        position=max_position + 1,
        uploaded_by=suggestion.user,
    )
    image.image_file.save(name, ContentFile(data), save=True)

    try:
        suggestion.pending_image.delete(save=False)
    except Exception:  # noqa: BLE001
        logger.exception(
            "_apply_photo_upload: failed to delete pending image %s "
            "for suggestion %s after copy — janitor will retry",
            suggestion.pending_image.name, suggestion.pk,
        )
    suggestion.pending_image = None
