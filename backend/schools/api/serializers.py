"""DRF serializers for School, Constituency, and DUN models."""

from rest_framework import serializers

from parliament.models import MP
from schools.models import Constituency, DUN, School, SchoolLeader
from schools.utils import format_phone


class SchoolListSerializer(serializers.ModelSerializer):
    """Compact school representation for list views."""

    constituency_code = serializers.CharField(
        source="constituency.code", default=None
    )
    constituency_name = serializers.CharField(
        source="constituency.name", default=None
    )
    dun_id = serializers.IntegerField(source="dun.id", default=None)
    dun_code = serializers.CharField(source="dun.code", default=None)
    dun_name = serializers.CharField(source="dun.name", default=None)
    image_url = serializers.SerializerMethodField()

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
            "dun_id",
            "dun_code",
            "dun_name",
            "enrolment",
            "teacher_count",
            "gps_lat",
            "gps_lng",
            "is_active",
            "assistance_type",
            "location_type",
            "preschool_enrolment",
            "special_enrolment",
            "image_url",
        ]

    def get_image_url(self, obj):
        """Return the primary image URL, or None."""
        primary = obj.images.filter(is_primary=True).first()
        if primary:
            return primary.image_url
        return None


class SchoolImageSerializer(serializers.Serializer):
    """Read-only serializer for school images."""

    image_url = serializers.URLField()
    source = serializers.CharField()
    is_primary = serializers.BooleanField()
    attribution = serializers.CharField()


class SchoolLeaderSerializer(serializers.ModelSerializer):
    """Public leader info — name and role only. Phone/email are private."""

    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = SchoolLeader
        fields = ["role", "role_display", "name"]


class SchoolDetailSerializer(serializers.ModelSerializer):
    """Full school profile for detail views."""

    constituency_code = serializers.CharField(
        source="constituency.code", default=None
    )
    constituency_name = serializers.CharField(
        source="constituency.name", default=None
    )
    dun_id = serializers.IntegerField(source="dun.id", default=None)
    dun_code = serializers.CharField(source="dun.code", default=None)
    dun_name = serializers.CharField(source="dun.name", default=None)
    phone = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    leaders = serializers.SerializerMethodField()

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
            "dun_id",
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
            "bank_name",
            "bank_account_number",
            "bank_account_name",
            "image_url",
            "images",
            "leaders",
        ]

    def get_phone(self, obj):
        """Return formatted phone number."""
        return format_phone(obj.phone)

    def get_image_url(self, obj):
        """Return the primary image URL for this school, or None."""
        primary = obj.images.filter(is_primary=True).first()
        if primary:
            return primary.image_url
        return None

    def get_images(self, obj):
        """Return all images for this school, primary first."""
        qs = obj.images.order_by("-is_primary", "-created_at")
        return SchoolImageSerializer(qs, many=True).data

    def get_leaders(self, obj):
        """Return active leaders in display order (board_chair, headmaster, pta_chair, alumni_chair)."""
        from django.db.models import Case, IntegerField, When

        qs = obj.leaders.filter(is_active=True).order_by(
            Case(
                When(role="board_chair", then=0),
                When(role="headmaster", then=1),
                When(role="pta_chair", then=2),
                When(role="alumni_chair", then=3),
                default=4,
                output_field=IntegerField(),
            )
        )
        return SchoolLeaderSerializer(qs, many=True).data


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
            "bank_name",
            "bank_account_number",
            "bank_account_name",
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


class MPSerializer(serializers.ModelSerializer):
    """Read-only MP contact details nested in constituency responses."""

    parlimen_profile_url = serializers.CharField(read_only=True)
    mymp_profile_url = serializers.CharField(read_only=True)

    class Meta:
        model = MP
        fields = [
            "name",
            "photo_url",
            "party",
            "email",
            "phone",
            "facebook_url",
            "twitter_url",
            "instagram_url",
            "website_url",
            "service_centre_address",
            "parlimen_profile_url",
            "mymp_profile_url",
        ]


class ConstituencyDetailSerializer(serializers.ModelSerializer):
    """Full constituency profile with nested schools and scorecard."""

    schools = SchoolListSerializer(many=True, read_only=True)
    scorecard = serializers.SerializerMethodField()
    mp = serializers.SerializerMethodField()
    electoral_influence = serializers.SerializerMethodField()

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
            "ge15_winning_margin",
            "ge15_total_voters",
            "ge15_indian_voter_pct",
            "schools",
            "scorecard",
            "mp",
            "electoral_influence",
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

    def get_mp(self, obj):
        try:
            return MPSerializer(obj.mp).data
        except MP.DoesNotExist:
            return None

    def get_electoral_influence(self, obj):
        margin = obj.ge15_winning_margin
        total_voters = obj.ge15_total_voters
        indian_pct = obj.ge15_indian_voter_pct
        if not margin:
            return None
        # Prefer voter ethnicity %, fall back to DOSM census indian_population
        if indian_pct and total_voters:
            indian_voters = int(float(total_voters) * float(indian_pct) / 100)
        elif obj.indian_population:
            indian_voters = obj.indian_population
        else:
            return None
        ratio = round(indian_voters / margin, 1) if margin > 0 else None
        if ratio is None:
            verdict = None
        elif ratio > 5:
            verdict = "kingmaker"
        elif ratio >= 1:
            verdict = "significant"
        else:
            verdict = "safe_seat"
        return {
            "indian_voters": indian_voters,
            "winning_margin": margin,
            "ratio": ratio,
            "verdict": verdict,
        }
