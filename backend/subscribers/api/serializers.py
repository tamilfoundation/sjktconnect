from rest_framework import serializers

from subscribers.models import Subscriber, SubscriptionPreference


class SubscribeSerializer(serializers.Serializer):
    """Serializer for the subscribe endpoint."""

    email = serializers.EmailField()
    name = serializers.CharField(max_length=200, required=False, default="", allow_blank=True)
    organisation = serializers.CharField(max_length=300, required=False, default="", allow_blank=True)


class SubscriberSerializer(serializers.ModelSerializer):
    """Read-only serializer for subscriber details."""

    preferences = serializers.SerializerMethodField()

    class Meta:
        model = Subscriber
        fields = ["email", "name", "organisation", "is_active", "subscribed_at", "preferences"]
        read_only_fields = fields

    def get_preferences(self, obj):
        return {
            pref.category: pref.is_enabled
            for pref in obj.preferences.all()
        }


class PreferenceUpdateSerializer(serializers.Serializer):
    """Serializer for updating subscription preferences."""

    PARLIAMENT_WATCH = serializers.BooleanField(required=False)
    NEWS_WATCH = serializers.BooleanField(required=False)
    MONTHLY_BLAST = serializers.BooleanField(required=False)

    def to_preference_dict(self):
        """Convert validated data to {category: is_enabled} dict."""
        return {
            key: value
            for key, value in self.validated_data.items()
            if value is not None
        }


class SubscriptionPreferenceSerializer(serializers.ModelSerializer):
    """Read-only serializer for individual preferences."""

    class Meta:
        model = SubscriptionPreference
        fields = ["category", "is_enabled"]
        read_only_fields = fields
