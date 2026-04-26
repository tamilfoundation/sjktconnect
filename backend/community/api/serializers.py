from rest_framework import serializers

from community.models import Suggestion


class SuggestionCreateSerializer(serializers.ModelSerializer):
    """Used for non-photo suggestions (DATA_CORRECTION, NOTE).

    PHOTO_UPLOAD does NOT go through this serializer — it has its own
    multipart endpoint that calls outreach.services.image_processor before
    creating the Suggestion. See community.api.views.school_suggestions_view
    branch on type.
    """

    class Meta:
        model = Suggestion
        fields = ["type", "field_name", "suggested_value", "note"]

    def validate_field_name(self, value):
        if value and value not in Suggestion.SUGGESTIBLE_FIELDS:
            if not value.startswith("leadership_"):
                raise serializers.ValidationError(f"Field '{value}' is not suggestible.")
        return value

    def validate(self, data):
        if data["type"] == "PHOTO_UPLOAD":
            raise serializers.ValidationError(
                "PHOTO_UPLOAD must use the multipart upload endpoint."
            )
        if data["type"] == "DATA_CORRECTION" and not data.get("field_name"):
            raise serializers.ValidationError(
                "field_name is required for data corrections."
            )
        return data


class SuggestionListSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.display_name", read_only=True)
    school_name = serializers.CharField(source="school.short_name", read_only=True)
    school_moe_code = serializers.CharField(source="school.moe_code", read_only=True)
    reviewed_by_name = serializers.SerializerMethodField()
    pending_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Suggestion
        fields = [
            "id", "school", "school_moe_code", "user_name", "school_name",
            "type", "status",
            "field_name", "current_value", "suggested_value", "note",
            "pending_image_url",
            "reviewed_by_name", "review_note", "points_awarded", "created_at",
        ]

    def get_reviewed_by_name(self, obj):
        if obj.reviewed_by:
            return obj.reviewed_by.display_name
        return None

    def get_pending_image_url(self, obj):
        """URL of the staged image for moderators. Empty string if none.

        Bucket is public-read but the path is a UUID — unguessable. Only
        surfaced through this authenticated serializer; not enumerable.
        """
        if not obj.pending_image:
            return ""
        try:
            return obj.pending_image.url
        except (ValueError, AttributeError):
            return ""
