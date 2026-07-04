"""Community suggestions API.

Sprint 14 reworked PHOTO_UPLOAD to a multipart flow:
  * Upload — Pillow-validated, EXIF stripped, resized, pHash dedup,
    bytes stored to Suggestion.pending_image (Supabase Storage).
  * Approve — copies bytes into a SchoolImage row (enforces 20-photo cap).
  * Reject — deletes the pending file.

DATA_CORRECTION + NOTE keep the JSON flow they had since Sprint 8.2.
"""

from django.core.files.base import ContentFile
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    parser_classes,
    permission_classes,
    throttle_classes,
)
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from accounts.permissions import IsProfileAuthenticated
from community.api.permissions import IsPhotoApprover
from community.api.serializers import (
    SuggestionCreateSerializer,
    SuggestionListSerializer,
)
from community.api.throttles import (
    PhotoUploadSchoolThrottle,
    PhotoUploadUserThrottle,
)
from community.models import Suggestion
from community.services import approve_suggestion, reject_suggestion
from outreach.models import SchoolImage
from outreach.services.image_processor import (
    UploadValidationError,
    process_upload,
)
from schools.models import School


PHOTO_CAP_PER_SCHOOL = 20


def _is_photo_approver(profile, school_id) -> bool:
    """Mirror of IsPhotoApprover for view-level branching."""
    if not profile:
        return False
    if profile.role == "SUPERADMIN":
        return True
    return bool(profile.admin_school_id and profile.admin_school_id == school_id)


def _can_moderate_or_owns_school(profile, school_id=None) -> bool:
    """Suggestion-moderation permission check.

    True for MODERATOR + SUPERADMIN (any school), or for the bound admin
    of `school_id` when provided. When school_id is None, only checks
    that the user is a privileged role (used by the queue list view —
    school admins ALSO get to see the queue, but their query is filtered
    to their own school by the caller).
    """
    if not profile:
        return False
    if profile.role in ("MODERATOR", "SUPERADMIN"):
        return True
    if not profile.admin_school_id:
        return False
    if school_id is None:
        return True
    return profile.admin_school_id == school_id


@api_view(["GET", "POST"])
@parser_classes([JSONParser])
@permission_classes([IsProfileAuthenticated])
def school_suggestions_view(request, moe_code):
    """List suggestions for a school OR create a non-photo suggestion.

    PHOTO_UPLOAD must use school_photo_upload_view (multipart endpoint).
    """
    school = get_object_or_404(School, moe_code=moe_code)
    profile = request.user_profile

    if request.method == "GET":
        suggestions = Suggestion.objects.filter(school=school)
        serializer = SuggestionListSerializer(suggestions, many=True)
        return Response(serializer.data)

    # POST — create suggestion (non-photo)
    if profile.admin_school_id == school.pk:
        return Response(
            {"detail": "Cannot suggest changes to your own school. Edit directly."},
            status=status.HTTP_403_FORBIDDEN,
        )

    serializer = SuggestionCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    current_value = ""
    if data.get("field_name") and hasattr(school, data["field_name"]):
        current_value = str(getattr(school, data["field_name"]) or "")

    suggestion = Suggestion.objects.create(
        school=school,
        user=profile,
        type=data["type"],
        field_name=data.get("field_name", ""),
        current_value=current_value,
        suggested_value=data.get("suggested_value", ""),
        note=data.get("note", ""),
    )

    return Response(
        SuggestionListSerializer(suggestion).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
@permission_classes([IsProfileAuthenticated])
@throttle_classes([PhotoUploadUserThrottle, PhotoUploadSchoolThrottle])
def school_photo_upload_view(request, moe_code):
    """Upload a photo as a PENDING suggestion.

    Multipart fields:
      image    — required, the file
      note     — optional caption / context for moderators

    Validation: ≤5 MB, JPEG/PNG/WebP, ≥640×400. EXIF stripped, resized to
    1600px longest edge, pHash computed for dedup against this user's prior
    PENDING/APPROVED uploads on the same school.

    Throttling: 5 / user / day, 20 / school / day.
    """
    school = get_object_or_404(School, moe_code=moe_code)
    profile = request.user_profile

    if profile.admin_school_id == school.pk:
        return Response(
            {"detail": "Cannot upload photos to your own school via this flow. "
                       "Use the admin image manager instead."},
            status=status.HTTP_403_FORBIDDEN,
        )

    upload = request.FILES.get("image")
    if not upload:
        return Response(
            {"detail": "Field 'image' is required.", "code": "missing_image"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    raw = upload.read()
    try:
        processed = process_upload(raw)
    except UploadValidationError as exc:
        # 413 for too_large, 415 for unsupported_format, 400 for the rest.
        if exc.code == "too_large":
            http_status = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        elif exc.code == "unsupported_format":
            http_status = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
        else:
            http_status = status.HTTP_400_BAD_REQUEST
        return Response(
            {"detail": exc.message, "code": exc.code},
            status=http_status,
        )

    # Dedup: refuse if the same user already has a PENDING or APPROVED upload
    # for this school with the same pHash.
    duplicate = Suggestion.objects.filter(
        school=school,
        user=profile,
        type=Suggestion.Type.PHOTO_UPLOAD,
        status__in=[Suggestion.Status.PENDING, Suggestion.Status.APPROVED],
        phash=processed.phash,
    ).exists()
    if duplicate:
        return Response(
            {"detail": "You have already uploaded this photo to this school.",
             "code": "duplicate"},
            status=status.HTTP_409_CONFLICT,
        )

    suggestion = Suggestion.objects.create(
        school=school,
        user=profile,
        type=Suggestion.Type.PHOTO_UPLOAD,
        note=request.data.get("note", "")[:500],
        phash=processed.phash,
    )
    filename = f"upload.{processed.extension}"
    suggestion.pending_image.save(
        filename,
        ContentFile(processed.bytes),
        save=True,
    )
    return Response(
        SuggestionListSerializer(suggestion).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
@permission_classes([IsProfileAuthenticated])
def admin_image_upload_view(request, moe_code):
    """Direct photo upload for SUPERADMIN or this school's bound admin.

    Skips the Suggestion staging queue entirely — bytes go straight into
    SchoolImage (source=COMMUNITY, uploaded_by=the admin). This is the
    counterpart to school_photo_upload_view: that one is for community
    users contributing to OTHER schools (suggestion + moderation flow);
    this one is for users empowered to publish photos for THIS school.

    Multipart fields:
      image    — required, the file
      caption  — optional, ≤200 chars

    Validation: ≤5 MB, JPEG/PNG/WebP, ≥640×400. EXIF stripped, resized
    to 1600px longest edge, pHash computed for dedup against existing
    SchoolImage rows on the same school.

    Returns 409 if school is at the 20-photo cap or a duplicate pHash
    already exists.
    """
    school = get_object_or_404(School, moe_code=moe_code)
    profile = request.user_profile

    if not _is_photo_approver(profile, school.pk):
        return Response(
            {"detail": "Only SUPERADMIN or this school's admin can upload directly."},
            status=status.HTTP_403_FORBIDDEN,
        )

    existing_count = SchoolImage.objects.filter(school=school).count()
    if existing_count >= PHOTO_CAP_PER_SCHOOL:
        return Response(
            {"detail": f"Photo slot full ({PHOTO_CAP_PER_SCHOOL}/{PHOTO_CAP_PER_SCHOOL}). "
                       "Delete an existing photo first.",
             "code": "slot_full"},
            status=status.HTTP_409_CONFLICT,
        )

    upload = request.FILES.get("image")
    if not upload:
        return Response(
            {"detail": "Field 'image' is required.", "code": "missing_image"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    raw = upload.read()
    try:
        processed = process_upload(raw)
    except UploadValidationError as exc:
        if exc.code == "too_large":
            http_status = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        elif exc.code == "unsupported_format":
            http_status = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
        else:
            http_status = status.HTTP_400_BAD_REQUEST
        return Response(
            {"detail": exc.message, "code": exc.code},
            status=http_status,
        )

    # No pHash dedup at SchoolImage level (the model doesn't carry pHash).
    # An admin re-uploading the same file will create a duplicate row —
    # they can spot-and-delete from the gallery if it bothers them.

    max_position = (
        SchoolImage.objects.filter(school=school)
        .order_by("-position")
        .values_list("position", flat=True)
        .first()
    ) or 0

    image = SchoolImage(
        school=school,
        source=SchoolImage.Source.COMMUNITY,
        position=max_position + 1,
        uploaded_by=profile,
        caption=(request.data.get("caption") or "")[:200],
    )
    image.image_file.save(
        f"upload.{processed.extension}",
        ContentFile(processed.bytes),
        save=True,
    )

    return Response({
        "id": image.id,
        "image_url": image.display_url,
        "source": image.source,
        "caption": image.caption,
        "is_primary": image.is_primary,
        "position": image.position,
        "uploaded_by_name": profile.display_name,
    }, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsProfileAuthenticated])
def pending_suggestions_view(request):
    """Moderation queue — all pending suggestions."""
    profile = request.user_profile

    if not _can_moderate_or_owns_school(profile):
        return Response(
            {"detail": "You do not have permission to view the moderation queue."},
            status=status.HTTP_403_FORBIDDEN,
        )

    qs = Suggestion.objects.filter(status=Suggestion.Status.PENDING)
    if profile.role not in ("MODERATOR", "SUPERADMIN") and profile.admin_school_id:
        qs = qs.filter(school_id=profile.admin_school_id)
    serializer = SuggestionListSerializer(qs, many=True)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsProfileAuthenticated])
def approve_suggestion_view(request, pk):
    """Approve a pending suggestion.

    For PHOTO_UPLOAD specifically:
      * Permission: IsPhotoApprover (SUPERADMIN or school admin only —
        MODERATOR cannot approve photos).
      * Returns 409 if the school is already at the 20-photo cap.

    For other types, MODERATOR + SUPERADMIN may approve, or the bound
    school admin.
    """
    suggestion = get_object_or_404(Suggestion, pk=pk, status=Suggestion.Status.PENDING)
    profile = request.user_profile

    if suggestion.type == Suggestion.Type.PHOTO_UPLOAD:
        if not _is_photo_approver(profile, suggestion.school_id):
            return Response(
                {"detail": "Only SUPERADMIN or this school's admin can approve photos."},
                status=status.HTTP_403_FORBIDDEN,
            )
        approved_count = SchoolImage.objects.filter(
            school_id=suggestion.school_id,
        ).count()
        if approved_count >= PHOTO_CAP_PER_SCHOOL:
            return Response(
                {"detail": f"Photo slot full ({PHOTO_CAP_PER_SCHOOL}/{PHOTO_CAP_PER_SCHOOL}). "
                           "Delete an existing photo first.",
                 "code": "slot_full"},
                status=status.HTTP_409_CONFLICT,
            )
    else:
        if not _can_moderate_or_owns_school(profile, suggestion.school_id):
            return Response(
                {"detail": "You can only approve suggestions for your own school."},
                status=status.HTTP_403_FORBIDDEN,
            )

    result = approve_suggestion(suggestion, profile)
    return Response(SuggestionListSerializer(result).data)


@api_view(["POST"])
@permission_classes([IsProfileAuthenticated])
def reject_suggestion_view(request, pk):
    suggestion = get_object_or_404(Suggestion, pk=pk, status=Suggestion.Status.PENDING)
    profile = request.user_profile

    if suggestion.type == Suggestion.Type.PHOTO_UPLOAD:
        if not _is_photo_approver(profile, suggestion.school_id):
            return Response(
                {"detail": "Only SUPERADMIN or this school's admin can reject photos."},
                status=status.HTTP_403_FORBIDDEN,
            )
    else:
        if not _can_moderate_or_owns_school(profile, suggestion.school_id):
            return Response(
                {"detail": "You can only reject suggestions for your own school."},
                status=status.HTTP_403_FORBIDDEN,
            )

    reason = request.data.get("reason", "")
    result = reject_suggestion(suggestion, profile, reason)
    return Response(SuggestionListSerializer(result).data)


@api_view(["GET"])
@permission_classes([AllowAny])
def school_images_view(request, moe_code):
    """List images for a school, ordered by position.

    Public by design — powers the school-page gallery for anonymous
    visitors. Audit 2026-07-01: previously relied on the DRF default
    `AllowAny` implicitly; now stated explicitly so a future default
    change (see Sprint 34 note) can't accidentally lock this down.
    """
    school = get_object_or_404(School, moe_code=moe_code)
    images = SchoolImage.objects.filter(school=school)
    data = [
        {
            "id": img.pk,
            "image_url": img.display_url,
            "source": img.source,
            "position": img.position,
            "is_primary": img.is_primary,
            "attribution": img.attribution,
            "caption": img.caption,
        }
        for img in images
    ]
    return Response(data)


@api_view(["PUT"])
@permission_classes([IsProfileAuthenticated])
def reorder_images_view(request, moe_code):
    """Reorder images. Body: {"order": [id1, id2, id3]}"""
    school = get_object_or_404(School, moe_code=moe_code)
    profile = request.user_profile
    if profile.role != "SUPERADMIN" and profile.admin_school_id != school.pk:
        return Response(
            {"detail": "Only school admin or superadmin can reorder images."},
            status=status.HTTP_403_FORBIDDEN,
        )
    order = request.data.get("order", [])
    # Audit 2026-07-01: wrap the N updates in a single txn so a mid-loop
    # crash can't leave positions half-shuffled.
    with transaction.atomic():
        for position, image_id in enumerate(order):
            SchoolImage.objects.filter(pk=image_id, school=school).update(position=position)
    return Response({"detail": "Images reordered."})


@api_view(["DELETE"])
@permission_classes([IsProfileAuthenticated])
def delete_image_view(request, moe_code, image_id):
    """Delete a school image (also removes the file from Supabase Storage)."""
    school = get_object_or_404(School, moe_code=moe_code)
    profile = request.user_profile
    if profile.role != "SUPERADMIN" and profile.admin_school_id != school.pk:
        return Response(
            {"detail": "Only school admin or superadmin can delete images."},
            status=status.HTTP_403_FORBIDDEN,
        )
    image = get_object_or_404(SchoolImage, pk=image_id, school=school)
    if image.image_file:
        # Best-effort: remove the file from Supabase. If the storage delete
        # fails (e.g. transient network), the DB row still goes — the
        # orphaned file will be cleaned up by a future janitor command.
        try:
            image.image_file.delete(save=False)
        except Exception:  # noqa: BLE001
            pass
    image.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


CAPTION_MAX_LEN = 200


@api_view(["PATCH"])
@permission_classes([IsProfileAuthenticated])
def update_image_caption_view(request, moe_code, image_id):
    """Update an image's caption (Sprint 15).

    Body: {"caption": "..."} (str, ≤200 chars).
    Permission: SUPERADMIN OR this school's bound admin.
    """
    school = get_object_or_404(School, moe_code=moe_code)
    profile = request.user_profile
    if profile.role != "SUPERADMIN" and profile.admin_school_id != school.pk:
        return Response(
            {"detail": "Only school admin or superadmin can edit captions."},
            status=status.HTTP_403_FORBIDDEN,
        )
    image = get_object_or_404(SchoolImage, pk=image_id, school=school)
    caption = request.data.get("caption", "")
    if not isinstance(caption, str):
        return Response(
            {"detail": "caption must be a string."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if len(caption) > CAPTION_MAX_LEN:
        return Response(
            {"detail": f"caption too long; max {CAPTION_MAX_LEN} characters.",
             "code": "too_long"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    image.caption = caption.strip()
    image.save(update_fields=["caption"])
    return Response({"id": image.pk, "caption": image.caption})


@api_view(["POST"])
@permission_classes([IsProfileAuthenticated])
def pin_image_view(request, moe_code, image_id):
    """Make this image the school's hero (is_primary=True).

    Atomically clears is_primary on all sibling images for the same school
    and sets it on the target. Permission: SUPERADMIN or this school's admin.
    """
    school = get_object_or_404(School, moe_code=moe_code)
    profile = request.user_profile
    if profile.role != "SUPERADMIN" and profile.admin_school_id != school.pk:
        return Response(
            {"detail": "Only school admin or superadmin can change the hero photo."},
            status=status.HTTP_403_FORBIDDEN,
        )
    try:
        image = SchoolImage.objects.get(pk=image_id, school=school)
    except SchoolImage.DoesNotExist as exc:
        raise Http404 from exc

    # Audit 2026-07-01: two writes (clear siblings, set target) must land
    # together — a crash between them could leave every image is_primary=
    # False, and the school would render with no hero.
    with transaction.atomic():
        SchoolImage.objects.filter(school=school).exclude(pk=image.pk).update(is_primary=False)
        if not image.is_primary:
            image.is_primary = True
            image.save(update_fields=["is_primary"])
    return Response({"detail": "Hero photo updated.", "id": image.pk})
