from rest_framework import serializers

from community.models import Suggestion


class SuggestionCreateSerializer(serializers.ModelSerializer):
    image = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Suggestion
        fields = ["type", "field_name", "suggested_value", "note", "image"]

    def validate_field_name(self, value):
        if value and value not in Suggestion.SUGGESTIBLE_FIELDS:
            if not value.startswith("leadership_"):
                raise serializers.ValidationError(f"Field '{value}' is not suggestible.")
        return value

    def validate(self, data):
        if data["type"] == "DATA_CORRECTION" and not data.get("field_name"):
            raise serializers.ValidationError(
                "field_name is required for data corrections."
            )
        if data["type"] == "PHOTO_UPLOAD" and not data.get("image"):
            raise serializers.ValidationError(
                "image is required for photo uploads."
            )
        return data


class SuggestionListSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.display_name", read_only=True)
    school_name = serializers.CharField(source="school.short_name", read_only=True)
    reviewed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Suggestion
        fields = [
            "id", "school", "user_name", "school_name", "type", "status",
            "field_name", "current_value", "suggested_value", "note",
            "reviewed_by_name", "review_note", "points_awarded", "created_at",
        ]

    def get_reviewed_by_name(self, obj):
        if obj.reviewed_by:
            return obj.reviewed_by.display_name
        return None
