"""DRF serializers for MPScorecard, SittingBrief, and ParliamentaryMeeting."""

from django.db.models import Sum
from rest_framework import serializers

from parliament.models import MPScorecard, ParliamentaryMeeting, SittingBrief


class MPScorecardSerializer(serializers.ModelSerializer):
    """MP Scorecard with constituency info."""

    constituency_code = serializers.CharField(
        source="constituency.code", default=None
    )
    constituency_name = serializers.CharField(
        source="constituency.name", default=None
    )

    class Meta:
        model = MPScorecard
        fields = [
            "id",
            "mp_name",
            "constituency_code",
            "constituency_name",
            "party",
            "coalition",
            "total_mentions",
            "substantive_mentions",
            "questions_asked",
            "commitments_made",
            "last_mention_date",
            "school_count",
            "total_enrolment",
        ]


class SchoolMentionSerializer(serializers.Serializer):
    """Approved Hansard mention for a school."""

    sitting_date = serializers.DateField(source="sitting.sitting_date")
    mp_name = serializers.CharField()
    mp_constituency = serializers.CharField()
    mp_party = serializers.CharField()
    mention_type = serializers.CharField()
    significance = serializers.IntegerField()
    sentiment = serializers.CharField()
    ai_summary = serializers.CharField()
    verbatim_quote = serializers.CharField()


class ConstituencyMentionSerializer(serializers.Serializer):
    """Hansard mention for a constituency's MP."""

    sitting_date = serializers.DateField(source="sitting.sitting_date")
    mp_name = serializers.CharField()
    mp_party = serializers.CharField()
    mention_type = serializers.CharField()
    significance = serializers.IntegerField()
    ai_summary = serializers.CharField()


class AllMentionSerializer(serializers.Serializer):
    """Hansard mention for the parliament-watch listing."""

    id = serializers.IntegerField()
    sitting_date = serializers.DateField(source="sitting.sitting_date")
    mp_name = serializers.CharField()
    mp_constituency = serializers.CharField()
    mp_party = serializers.CharField()
    mention_type = serializers.CharField()
    significance = serializers.IntegerField()
    sentiment = serializers.CharField()
    ai_summary = serializers.CharField()
    schools = serializers.SerializerMethodField()

    def get_schools(self, obj):
        return [
            {"name": ms.school.name, "moe_code": ms.school.moe_code}
            for ms in obj.matched_schools.select_related("school").all()
        ]


class SittingBriefSerializer(serializers.ModelSerializer):
    """Sitting brief."""

    sitting_date = serializers.DateField(source="sitting.sitting_date")
    mention_count = serializers.IntegerField(source="sitting.mention_count")

    class Meta:
        model = SittingBrief
        fields = [
            "id",
            "sitting_date",
            "title",
            "summary_html",
            "social_post_text",
            "mention_count",
            "published_at",
        ]


class MeetingReportSerializer(serializers.ModelSerializer):
    """Parliamentary meeting report with computed sitting/mention counts."""

    sitting_count = serializers.SerializerMethodField()
    total_mentions = serializers.SerializerMethodField()
    illustration_url = serializers.SerializerMethodField()

    class Meta:
        model = ParliamentaryMeeting
        fields = [
            "id",
            "name",
            "short_name",
            "term",
            "session",
            "year",
            "start_date",
            "end_date",
            "report_html",
            "executive_summary",
            "social_post_text",
            "sitting_count",
            "total_mentions",
            "illustration_url",
            "published_at",
        ]

    def get_sitting_count(self, obj):
        if hasattr(obj, "_sitting_count"):
            return obj._sitting_count
        return obj.sittings.count()

    def get_total_mentions(self, obj):
        if hasattr(obj, "_total_mentions"):
            return obj._total_mentions
        return obj.sittings.aggregate(
            total=Sum("mention_count")
        )["total"] or 0

    def get_illustration_url(self, obj):
        if obj.illustration:
            request = self.context.get("request")
            path = f"/api/v1/meetings/{obj.pk}/illustration/"
            if request:
                return request.build_absolute_uri(path)
            return path
        return None
