from rest_framework import serializers

from accounts.models import UserProfile
from schools.models import School


class GoogleAuthSerializer(serializers.Serializer):
    id_token = serializers.CharField()


class UserProfileSerializer(serializers.ModelSerializer):
    admin_school = serializers.SerializerMethodField()
    email = serializers.EmailField(source="user.email", read_only=True)
    pending_moderation_count = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            "id", "google_id", "display_name", "avatar_url",
            "role", "admin_school", "points", "is_active",
            "email", "pending_moderation_count",
        ]
        read_only_fields = fields

    def get_admin_school(self, obj):
        if obj.admin_school:
            return {
                "moe_code": obj.admin_school.moe_code,
                "name": obj.admin_school.short_name,
            }
        return None

    def get_pending_moderation_count(self, obj):
        """PENDING Suggestion rows this user is empowered to review.

        SUPERADMIN / MODERATOR see all; bound school admin sees only
        their school's queue; plain USER returns 0 (badge stays hidden).
        Drives the avatar badge + dropdown deep-link in UserMenu.
        """
        from community.models import Suggestion
        if obj.role in ("SUPERADMIN", "MODERATOR"):
            return Suggestion.objects.filter(status=Suggestion.Status.PENDING).count()
        if obj.admin_school_id:
            return Suggestion.objects.filter(
                status=Suggestion.Status.PENDING,
                school_id=obj.admin_school_id,
            ).count()
        return 0


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Self-service profile update — only display_name is user-editable."""

    class Meta:
        model = UserProfile
        fields = ["display_name"]

    def validate_display_name(self, value):
        value = value.strip()
        if len(value) < 1:
            raise serializers.ValidationError("Display name cannot be empty.")
        if len(value) > 200:
            raise serializers.ValidationError("Display name cannot exceed 200 characters.")
        return value


class UserProfileAdminListSerializer(serializers.ModelSerializer):
    """Listing view for SUPERADMIN /dashboard/users."""

    admin_school = serializers.SerializerMethodField()
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            "id", "display_name", "avatar_url", "email",
            "role", "admin_school", "points", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_admin_school(self, obj):
        if obj.admin_school:
            return {
                "moe_code": obj.admin_school.moe_code,
                "name": obj.admin_school.short_name,
            }
        return None


class UserProfileAdminUpdateSerializer(serializers.ModelSerializer):
    """SUPERADMIN-only mutable fields. admin_school accepts a moe_code string or null."""

    admin_school = serializers.CharField(
        allow_null=True, required=False,
        help_text="School moe_code to assign, or null to unassign",
    )

    class Meta:
        model = UserProfile
        fields = ["role", "admin_school", "is_active"]

    def validate_role(self, value):
        valid = [choice[0] for choice in UserProfile.Role.choices]
        if value not in valid:
            raise serializers.ValidationError(f"Role must be one of {valid}.")
        return value

    def validate_admin_school(self, value):
        if value is None or value == "":
            return None
        try:
            school = School.objects.get(moe_code=value, is_active=True)
        except School.DoesNotExist:
            raise serializers.ValidationError(f"School '{value}' not found or inactive.")
        return school

    def update(self, instance, validated_data):
        # admin_school came in as a School instance (or None) from validate_admin_school
        if "admin_school" in validated_data:
            school = validated_data.pop("admin_school")
            # Another profile already admin of this school? Swap them off.
            if school is not None:
                UserProfile.objects.filter(admin_school=school).exclude(id=instance.id).update(
                    admin_school=None
                )
            instance.admin_school = school
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
