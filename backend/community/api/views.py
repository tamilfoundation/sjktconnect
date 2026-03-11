import base64

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from accounts.permissions import IsProfileAuthenticated
from community.api.serializers import SuggestionCreateSerializer, SuggestionListSerializer
from community.models import Suggestion
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
