from rest_framework import serializers

from accounts.models import UserProfile


class GoogleAuthSerializer(serializers.Serializer):
    id_token = serializers.CharField()


class UserProfileSerializer(serializers.ModelSerializer):
    admin_school = serializers.SerializerMethodField()
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            "id", "google_id", "display_name", "avatar_url",
            "role", "admin_school", "points", "is_active",
            "email",
        ]
        read_only_fields = fields

    def get_admin_school(self, obj):
        if obj.admin_school:
            return {
                "moe_code": obj.admin_school.moe_code,
                "name": obj.admin_school.short_name,
            }
        return None
