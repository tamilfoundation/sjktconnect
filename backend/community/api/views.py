import base64

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from accounts.permissions import IsProfileAuthenticated
from community.api.serializers import SuggestionCreateSerializer, SuggestionListSerializer
from community.models import Suggestion
from community.services import approve_suggestion, reject_suggestion
from outreach.models import SchoolImage
from schools.models import School


@api_view(["GET", "POST"])
@permission_classes([IsProfileAuthenticated])
def school_suggestions_view(request, moe_code):
    school = get_object_or_404(School, moe_code=moe_code)
    profile = request.user_profile

    if request.method == "GET":
        suggestions = Suggestion.objects.filter(school=school)
        serializer = SuggestionListSerializer(suggestions, many=True)
        return Response(serializer.data)

    # POST — create suggestion
    if profile.admin_school_id == school.pk:
        return Response(
            {"detail": "Cannot suggest changes to your own school. Edit directly."},
            status=status.HTTP_403_FORBIDDEN,
        )

    serializer = SuggestionCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    # Snapshot current value for data corrections
    current_value = ""
    if data.get("field_name") and hasattr(school, data["field_name"]):
        current_value = str(getattr(school, data["field_name"]) or "")

    # Handle base64 image
    image_bytes = b""
    if data.get("image"):
        try:
            image_bytes = base64.b64decode(data["image"])
        except Exception:
            return Response(
                {"detail": "Invalid image data."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    suggestion = Suggestion.objects.create(
        school=school,
        user=profile,
        type=data["type"],
        field_name=data.get("field_name", ""),
        current_value=current_value,
        suggested_value=data.get("suggested_value", ""),
        note=data.get("note", ""),
        image=image_bytes,
    )

    return Response(
        SuggestionListSerializer(suggestion).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([IsProfileAuthenticated])
def pending_suggestions_view(request):
    """Moderation queue — all pending suggestions."""
    profile = request.user_profile

    # Must be moderator, superadmin, or school admin
    if profile.role not in ("MODERATOR", "SUPERADMIN") and not profile.admin_school_id:
        return Response(
            {"detail": "You do not have permission to view the moderation queue."},
            status=status.HTTP_403_FORBIDDEN,
        )

    qs = Suggestion.objects.filter(status=Suggestion.Status.PENDING)
    # School admins see only their school
    if profile.role not in ("MODERATOR", "SUPERADMIN") and profile.admin_school_id:
        qs = qs.filter(school_id=profile.admin_school_id)
    serializer = SuggestionListSerializer(qs, many=True)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsProfileAuthenticated])
def approve_suggestion_view(request, pk):
    suggestion = get_object_or_404(Suggestion, pk=pk, status=Suggestion.Status.PENDING)
    profile = request.user_profile
    if profile.role not in ("MODERATOR", "SUPERADMIN"):
        if profile.admin_school_id != suggestion.school_id:
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
    if profile.role not in ("MODERATOR", "SUPERADMIN"):
        if profile.admin_school_id != suggestion.school_id:
            return Response(
                {"detail": "You can only reject suggestions for your own school."},
                status=status.HTTP_403_FORBIDDEN,
            )
    reason = request.data.get("reason", "")
    result = reject_suggestion(suggestion, profile, reason)
    return Response(SuggestionListSerializer(result).data)


@api_view(["GET"])
def suggestion_image_view(request, pk):
    """Serve a suggestion's uploaded image as PNG."""
    suggestion = get_object_or_404(Suggestion, pk=pk)
    if not suggestion.image:
        return Response(status=status.HTTP_404_NOT_FOUND)
    return HttpResponse(bytes(suggestion.image), content_type="image/png")


@api_view(["GET"])
def school_images_view(request, moe_code):
    """List images for a school, ordered by position."""
    school = get_object_or_404(School, moe_code=moe_code)
    images = SchoolImage.objects.filter(school=school)
    data = [
        {
            "id": img.pk,
            "image_url": img.image_url,
            "source": img.source,
            "position": img.position,
            "is_primary": img.is_primary,
            "attribution": img.attribution,
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
    if profile.role != "SUPERADMIN" and profile.admin_school_id != school.moe_code:
        return Response(
            {"detail": "Only school admin or superadmin can reorder images."},
            status=status.HTTP_403_FORBIDDEN,
        )
    order = request.data.get("order", [])
    for position, image_id in enumerate(order):
        SchoolImage.objects.filter(pk=image_id, school=school).update(position=position)
    return Response({"detail": "Images reordered."})


@api_view(["DELETE"])
@permission_classes([IsProfileAuthenticated])
def delete_image_view(request, moe_code, image_id):
    """Delete a school image."""
    school = get_object_or_404(School, moe_code=moe_code)
    profile = request.user_profile
    if profile.role != "SUPERADMIN" and profile.admin_school_id != school.moe_code:
        return Response(
            {"detail": "Only school admin or superadmin can delete images."},
            status=status.HTTP_403_FORBIDDEN,
        )
    image = get_object_or_404(SchoolImage, pk=image_id, school=school)
    image.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
