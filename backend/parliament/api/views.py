"""API views for MPScorecard, SittingBrief, and SchoolMentions."""

from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView, RetrieveAPIView

from hansard.models import HansardMention
from parliament.api.serializers import (
    MPScorecardSerializer,
    SchoolMentionSerializer,
    SittingBriefSerializer,
)
from parliament.models import MPScorecard, SittingBrief
from schools.models import School


class MPScorecardListView(ListAPIView):
    """List all MP scorecards.

    Filters: ?constituency=, ?party=
    """

    serializer_class = MPScorecardSerializer

    def get_queryset(self):
        qs = MPScorecard.objects.select_related("constituency")
        constituency = self.request.query_params.get("constituency")
        party = self.request.query_params.get("party")
        if constituency:
            qs = qs.filter(constituency__code=constituency)
        if party:
            qs = qs.filter(party__icontains=party)
        return qs


class MPScorecardDetailView(RetrieveAPIView):
    """Retrieve a single MP scorecard."""

    serializer_class = MPScorecardSerializer
    queryset = MPScorecard.objects.select_related("constituency")


class SittingBriefListView(ListAPIView):
    """List published sitting briefs only."""

    serializer_class = SittingBriefSerializer
    queryset = SittingBrief.objects.filter(
        is_published=True,
    ).select_related("sitting")


class SittingBriefDetailView(RetrieveAPIView):
    """Retrieve a single published sitting brief."""

    serializer_class = SittingBriefSerializer
    queryset = SittingBrief.objects.filter(
        is_published=True,
    ).select_related("sitting")


class SchoolMentionsView(ListAPIView):
    """List approved Hansard mentions for a school."""

    serializer_class = SchoolMentionSerializer
    authentication_classes = []
    permission_classes = []
    pagination_class = None

    def get_queryset(self):
        school = get_object_or_404(School, moe_code=self.kwargs["moe_code"])
        return (
            HansardMention.objects.filter(
                matched_schools__school=school,
                review_status="APPROVED",
            )
            .select_related("sitting")
            .order_by("-sitting__sitting_date")
        )
