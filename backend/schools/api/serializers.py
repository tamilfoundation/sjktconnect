"""DRF serializers for School, Constituency, and DUN models."""

from rest_framework import serializers

from schools.models import Constituency, DUN, School


class SchoolListSerializer(serializers.ModelSerializer):
    """Compact school representation for list views."""

    constituency_code = serializers.CharField(
        source="constituency.code", default=None
    )
    constituency_name = serializers.CharField(
        source="constituency.name", default=None
    )

    class Meta:
        model = School
        fields = [
            "moe_code",
            "name",
            "short_name",
            "state",
            "ppd",
            "constituency_code",
            "constituency_name",
            "enrolment",
            "teacher_count",
            "gps_lat",
            "gps_lng",
            "is_active",
        ]


class SchoolDetailSerializer(serializers.ModelSerializer):
    """Full school profile for detail views."""

    constituency_code = serializers.CharField(
        source="constituency.code", default=None
    )
    constituency_name = serializers.CharField(
        source="constituency.name", default=None
    )
    dun_code = serializers.CharField(source="dun.code", default=None)
    dun_name = serializers.CharField(source="dun.name", default=None)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = School
        fields = [
            "moe_code",
            "name",
            "short_name",
            "name_tamil",
            "address",
            "postcode",
            "city",
            "state",
            "ppd",
            "constituency_code",
            "constituency_name",
            "dun_code",
            "dun_name",
            "email",
            "phone",
            "fax",
            "gps_lat",
            "gps_lng",
            "gps_verified",
            "enrolment",
            "preschool_enrolment",
            "special_enrolment",
            "teacher_count",
            "grade",
            "assistance_type",
            "session_count",
            "session_type",
            "skm_eligible",
            "location_type",
            "is_active",
            "last_verified",
            "image_url",
        ]

    def get_image_url(self, obj):
        """Return the primary image URL for this school, or None."""
        primary = obj.images.filter(is_primary=True).first()
        if primary:
            return primary.image_url
        return None


class SchoolEditSerializer(serializers.ModelSerializer):
    """Writable serializer for school reps to confirm/edit their school data.

    Only exposes fields that school representatives should be able to update.
    Read-only fields (moe_code, name, short_name, state) are included for display
    but cannot be modified.
    """

    class Meta:
        model = School
        fields = [
            "moe_code",
            "name",
            "short_name",
            "name_tamil",
            "address",
            "postcode",
            "city",
            "state",
            "email",
            "phone",
            "fax",
            "gps_lat",
            "gps_lng",
            "enrolment",
            "preschool_enrolment",
            "special_enrolment",
            "teacher_count",
            "session_count",
            "session_type",
            "last_verified",
            "verified_by",
        ]
        read_only_fields = [
            "moe_code",
            "name",
            "short_name",
            "state",
            "last_verified",
            "verified_by",
        ]


class DUNListSerializer(serializers.ModelSerializer):
    """Compact DUN for list views."""

    constituency_code = serializers.CharField(source="constituency.code")

    class Meta:
        model = DUN
        fields = [
            "id",
            "code",
            "name",
            "state",
            "constituency_code",
            "adun_name",
            "adun_party",
        ]


class DUNDetailSerializer(serializers.ModelSerializer):
    """Full DUN profile with nested schools."""

    constituency_code = serializers.CharField(source="constituency.code")
    constituency_name = serializers.CharField(source="constituency.name")
    schools = SchoolListSerializer(many=True, read_only=True)

    class Meta:
        model = DUN
        fields = [
            "id",
            "code",
            "name",
            "state",
            "constituency_code",
            "constituency_name",
            "adun_name",
            "adun_party",
            "adun_coalition",
            "indian_population",
            "indian_percentage",
            "schools",
        ]


class ConstituencyListSerializer(serializers.ModelSerializer):
    """Compact constituency for list views."""

    school_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Constituency
        fields = [
            "code",
            "name",
            "state",
            "mp_name",
            "mp_party",
            "school_count",
        ]


class ConstituencyDetailSerializer(serializers.ModelSerializer):
    """Full constituency profile with nested schools and scorecard."""

    schools = SchoolListSerializer(many=True, read_only=True)
    scorecard = serializers.SerializerMethodField()

    class Meta:
        model = Constituency
        fields = [
            "code",
            "name",
            "state",
            "mp_name",
            "mp_party",
            "mp_coalition",
            "indian_population",
            "indian_percentage",
            "avg_income",
            "poverty_rate",
            "gini",
            "unemployment_rate",
            "schools",
            "scorecard",
        ]

    def get_scorecard(self, obj):
        scorecard = obj.scorecards.first()
        if not scorecard:
            return None
        return {
            "total_mentions": scorecard.total_mentions,
            "substantive_mentions": scorecard.substantive_mentions,
            "questions_asked": scorecard.questions_asked,
            "commitments_made": scorecard.commitments_made,
            "last_mention_date": scorecard.last_mention_date,
        }
