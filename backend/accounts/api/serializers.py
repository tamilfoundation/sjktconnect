from rest_framework import serializers

from accounts.models import UserProfile


class RequestMagicLinkSerializer(serializers.Serializer):
    email = serializers.EmailField()


class VerifyTokenSerializer(serializers.Serializer):
    school_moe_code = serializers.CharField(source="school.moe_code")
    school_name = serializers.CharField(source="school.short_name")
    email = serializers.EmailField()


class SchoolContactSerializer(serializers.Serializer):
    school_moe_code = serializers.CharField(source="school.moe_code")
    school_name = serializers.CharField(source="school.short_name")
    email = serializers.EmailField()
    name = serializers.CharField()
    role = serializers.CharField()
    verified_at = serializers.DateTimeField()


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
