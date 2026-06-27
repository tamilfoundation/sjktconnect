"""DRF serializers for School, Constituency, and DUN models."""

from decimal import Decimal, ROUND_HALF_UP

from rest_framework import serializers

from parliament.models import MP
from schools.models import Constituency, DUN, School, SchoolLeader
from schools.utils import format_phone


# Sprint 28 follow-up: School.gps_lat / gps_lng are
# DecimalField(max_digits=10, decimal_places=7). DRF rejects inputs with
# more than 7 decimal places (400). Frontend admin edit pastes Google
# Maps values (15+ JS-double digits) which triggers the reject. Round
# down to 7 dp before validation so the field accepts.
_GPS_QUANT = Decimal("0.0000001")


def _quantize_gps(value, field_name):
    if value in (None, ""):
        return value
    try:
        return Decimal(str(value)).quantize(_GPS_QUANT, rounding=ROUND_HALF_UP)
    except Exception as exc:
        raise serializers.ValidationError(
            f"{field_name} must be a numeric value."
        ) from exc


def _normalise_phone(value):
    """Run a phone string through format_phone() but preserve sentinel
    no-value markers (TIADA / N/A / -) verbatim."""
    if not value:
        return value
    if value.strip().lower() in ("tiada", "n/a", "na", "none", "-"):
        return value
    formatted = format_phone(value)
    # format_phone returns the original input if unparseable; either
    # way the result is what we want to store.
    return formatted


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
        """Return the primary image URL, or None.

        Uses display_url so Sprint 13-migrated rows (where the legacy
        image_url field is empty and bytes live in image_file via Supabase
        Storage) return the Supabase URL instead of an empty string.
        """
        primary = obj.images.filter(is_primary=True).first()
        if primary:
            return primary.display_url or None
        return None


class SchoolMapSerializer(serializers.ModelSerializer):
    """Minimal school data for map pins — 11 fields. Sprint 28 added
    `city` so the sitemap and internal-link generators can build the
    canonical slug URL (which includes city for SEO parity with
    apac.com.my-style URLs)."""

    class Meta:
        model = School
        fields = [
            "moe_code",
            "short_name",
            "gps_lat",
            "gps_lng",
            "enrolment",
            "preschool_enrolment",
            "special_enrolment",
            "assistance_type",
            "location_type",
            "state",
            "city",
        ]


class SchoolImageSerializer(serializers.Serializer):
    """Read-only serializer for school images.

    Sprint 13: image_url returns Supabase Storage URL (image_file.url) when
    set, falling back to legacy image_url for unmigrated rows.
    """

    id = serializers.IntegerField()
    image_url = serializers.SerializerMethodField()
    source = serializers.CharField()
    is_primary = serializers.BooleanField()
    attribution = serializers.CharField()
    caption = serializers.CharField()

    def get_image_url(self, obj):
        return obj.display_url


class SchoolLeaderSerializer(serializers.ModelSerializer):
    """Public leader info — name and role only. Phone/email are private."""

    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = SchoolLeader
        fields = ["role", "role_display", "name"]


class SchoolLeaderAdminSerializer(serializers.ModelSerializer):
    """Sprint 20 — admin-only serializer for the leader CRUD endpoints.

    Includes phone + email (private fields) which the public
    SchoolLeaderSerializer omits. Role is required on create but
    immutable on update — to change a leader's role, delete and
    re-create.

    Sprint 26 #1: phone is validated the same way as School.phone so
    a multi-number string like "05-2421470/011-2379104" is rejected
    server-side, not just at the React form layer.
    """

    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = SchoolLeader
        fields = ["id", "role", "role_display", "name", "phone", "email"]
        read_only_fields = ["id", "role_display"]

    def validate_phone(self, value):
        if not value:
            return value
        if value.strip().lower() in ("tiada", "n/a", "na", "none", "-"):
            return value
        import re
        if not re.fullmatch(r"[\d+\-\s()]{6,20}", value):
            raise serializers.ValidationError(
                "phone must contain only digits, spaces, +, -, or brackets, "
                "6-20 chars (no '/' for multi-number). Use 'TIADA' if none."
            )
        # Sprint 28 follow-up: normalise to +60-X XXX XXXX format so
        # leader phones display consistently with MOE-imported School
        # phones. Owner-flagged 2026-06-26: leader 0122090008 looked
        # inconsistent next to school +60-5 548 4299.
        return _normalise_phone(value)

    def update(self, instance, validated_data):
        # Role is set at creation and cannot be changed via PATCH.
        validated_data.pop("role", None)
        return super().update(instance, validated_data)


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
    is_claimed = serializers.SerializerMethodField()

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
            "claimed_at",
            "is_claimed",
            "bank_name",
            "bank_account_number",
            "bank_account_name",
            "image_url",
            "images",
            "leaders",
            "history",
            "history_source_urls",
            "history_status",
            "history_updated_at",
            "history_key_dates",
        ]

    def get_is_claimed(self, obj):
        """True if a UserProfile has admin_school bound to this school."""
        return obj.claimed_at is not None

    def get_phone(self, obj):
        """Return formatted phone number."""
        return format_phone(obj.phone)

    def get_image_url(self, obj):
        """Return the primary image URL for this school, or None.

        Sprint 13: prefers Supabase Storage (image_file.url) over the legacy
        image_url. SchoolImage.display_url encapsulates the fallback.
        """
        primary = obj.images.filter(is_primary=True).first()
        if primary:
            return primary.display_url or None
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
    """Writable serializer for school reps to edit their school data.

    Only exposes fields that school representatives should be able to update.
    Read-only fields (moe_code, name, short_name, state, plus the MOE-source
    metadata in the Sprint 19 extension below) are included for display
    but cannot be modified.

    Sprint 19 (2026-04-28) added the read-only MOE metadata + leaders so the
    tabbed edit page renders from a single endpoint call.
    Sprint 26 (2026-06-26) added server-side phone validators that mirror
    the frontend rule (digits + space + - + + + brackets only; no `/`).
    Front-end validation is the primary UX; back-end is the safety net
    against curl + admin shell edits.
    """

    leaders = serializers.SerializerMethodField()

    # Sprint 26 #1: refuse multi-number phone strings at the API layer.
    # The frontend already shows an inline error, but a determined
    # operator who curls the endpoint must still be blocked.
    # Sprint 28 follow-up: MOE uses "TIADA" (Bahasa for "none") as the
    # canonical no-phone marker; accept it explicitly (any case).
    def _validate_phone_like(self, value, field_name):
        if not value:
            return value
        if value.strip().lower() in ("tiada", "n/a", "na", "none", "-"):
            return value
        import re
        if not re.fullmatch(r"[\d+\-\s()]{6,20}", value):
            raise serializers.ValidationError(
                f"{field_name} must contain only digits, spaces, +, -, or "
                f"brackets, 6-20 chars (no '/' for multi-number). "
                "Use 'TIADA' if the school has no number."
            )
        return value

    def validate_phone(self, value):
        return _normalise_phone(self._validate_phone_like(value, "phone"))

    def validate_fax(self, value):
        return _normalise_phone(self._validate_phone_like(value, "fax"))

    def validate_gps_lat(self, value):
        return _quantize_gps(value, "gps_lat")

    def validate_gps_lng(self, value):
        return _quantize_gps(value, "gps_lng")

    def validate_session_type(self, value):
        # Sprint 26 #2: constrain Session Type to MOE-published values.
        # Empty string is fine — MOE hasn't always provided this field.
        if value and value not in ("Pagi Sahaja", "Pagi dan Petang"):
            raise serializers.ValidationError(
                "session_type must be empty, 'Pagi Sahaja', or 'Pagi dan Petang'."
            )
        return value

    def get_leaders(self, obj):
        # Sprint 20: edit-page consumers need the admin shape (id +
        # phone + email) for inline CRUD. The endpoint is gated by
        # IsProfileAuthenticated AND the view checks bound-school-admin /
        # SUPERADMIN before returning anything, so private fields are
        # safe to expose here.
        qs = obj.leaders.filter(is_active=True).order_by(
            # Match SchoolDetailSerializer ordering: Chairman → HM → PTA → Alumni
            "role"
        )
        return SchoolLeaderAdminSerializer(qs, many=True).data

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
            # Sprint 19: extra read-only MOE fields surfaced on the
            # tabbed edit page so the Core + Contact tabs can show
            # full context without a second API call.
            "ppd",
            "grade",
            "assistance_type",
            "skm_eligible",
            "location_type",
            "gps_lat",
            "gps_lng",
            "gps_verified",
            "claimed_at",
            "leaders",
            # Sprint 31 (2026-06-27): school history (per-locale JSON +
            # source URLs + status). All three writable by SUPERADMIN
            # AND bound school admin. Status auto-flips to SCHOOL_REVIEWED
            # on save by a non-SUPERADMIN; SUPERADMIN can set any status.
            "history",
            "history_source_urls",
            "history_status",
            "history_updated_at",
            "history_key_dates",
        ]
        # NOTE: gps_lat + gps_lng are conditionally writable — see
        # SchoolEditSerializer.update() below. They're NOT in
        # read_only_fields so DRF will pass them through to validated_data;
        # the override drops them when the request user isn't SUPERADMIN.
        # Owner-reported bug 2026-06-26: keeping them in read_only_fields
        # silently dropped SUPERADMIN GPS edits, leaving the user with a
        # green "Changes saved" message but stale data on the public page.
        read_only_fields = [
            "moe_code",
            "name",
            "short_name",
            "state",
            "ppd",
            "grade",
            "assistance_type",
            "skm_eligible",
            "location_type",
            "gps_verified",
            "claimed_at",
            "leaders",
            "history_updated_at",  # auto-managed in update()
        ]

    def validate_history(self, value):
        """history is a per-locale dict {en, ms, ta}. Strip unknowns; cap length."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("history must be an object {en, ms, ta}.")
        allowed = {"en", "ms", "ta"}
        unknown = set(value.keys()) - allowed
        if unknown:
            raise serializers.ValidationError(
                f"history allows only keys en/ms/ta. Got unknown: {sorted(unknown)}"
            )
        for locale, text in value.items():
            if not isinstance(text, str):
                raise serializers.ValidationError(
                    f"history.{locale} must be a string."
                )
            if len(text) > 5000:
                raise serializers.ValidationError(
                    f"history.{locale} too long ({len(text)} chars; max 5000)."
                )
        return value

    def validate_history_source_urls(self, value):
        """list of http(s) URLs. Cap length."""
        if not isinstance(value, list):
            raise serializers.ValidationError("history_source_urls must be a list.")
        if len(value) > 10:
            raise serializers.ValidationError("max 10 source URLs.")
        for url in value:
            if not isinstance(url, str) or not url.startswith(("http://", "https://")):
                raise serializers.ValidationError(
                    f"Each source URL must start with http:// or https://. Got: {url!r}"
                )
        return value

    def update(self, instance, validated_data):
        # Only SUPERADMINs may update GPS — school admins see the fields
        # as read-only badges (Sprint 5.4's batch-verified pins). The
        # frontend gates the UI, this guard is the trust boundary.
        request = self.context.get("request")
        profile_id = (
            request.session.get("user_profile_id") if request else None
        )
        is_superadmin = False
        if profile_id:
            from accounts.models import UserProfile
            try:
                profile = UserProfile.objects.get(pk=profile_id)
                is_superadmin = profile.role == "SUPERADMIN"
            except UserProfile.DoesNotExist:
                pass
        if not is_superadmin:
            validated_data.pop("gps_lat", None)
            validated_data.pop("gps_lng", None)
            # Sprint 31: non-SUPERADMIN edits flip status to SCHOOL_REVIEWED.
            # SUPERADMIN can pass any status explicitly (incl. VERIFIED).
            if "history" in validated_data or "history_source_urls" in validated_data:
                validated_data.pop("history_status", None)  # ignore client value
                validated_data["history_status"] = "SCHOOL_REVIEWED"
        # Bump history_updated_at whenever history content changes (any role).
        if "history" in validated_data or "history_source_urls" in validated_data:
            from django.utils import timezone
            validated_data["history_updated_at"] = timezone.now()
        return super().update(instance, validated_data)


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
