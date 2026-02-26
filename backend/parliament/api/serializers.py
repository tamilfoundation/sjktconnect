"""DRF serializers for MPScorecard and SittingBrief models."""

from rest_framework import serializers

from parliament.models import MPScorecard, SittingBrief


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


class SittingBriefSerializer(serializers.ModelSerializer):
    """Published sitting brief."""

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
