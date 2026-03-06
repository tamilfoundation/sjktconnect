"""API views for MPScorecard, SittingBrief, ParliamentaryMeeting, and SchoolMentions."""

from django.db.models import Count, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView, RetrieveAPIView

from hansard.models import HansardMention
from parliament.api.serializers import (
    AllMentionSerializer,
    ConstituencyMentionSerializer,
    MeetingReportSerializer,
    MPScorecardSerializer,
    SchoolMentionSerializer,
    SittingBriefSerializer,
)
from parliament.models import MPScorecard, ParliamentaryMeeting, SittingBrief
from schools.models import Constituency, School


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
    """List sitting briefs (all that have content)."""

    serializer_class = SittingBriefSerializer
    queryset = (
        SittingBrief.objects.exclude(summary_html="")
        .select_related("sitting")
        .order_by("-sitting__sitting_date")
    )


class SittingBriefDetailView(RetrieveAPIView):
    """Retrieve a single sitting brief."""

    serializer_class = SittingBriefSerializer
    queryset = SittingBrief.objects.exclude(summary_html="").select_related("sitting")


class AllMentionsListView(ListAPIView):
    """List all non-rejected Hansard mentions (paginated).

    For the parliament-watch page.
    """

    serializer_class = AllMentionSerializer

    def get_queryset(self):
        return (
            HansardMention.objects.exclude(review_status="REJECTED")
            .exclude(ai_summary="")
            .select_related("sitting")
            .prefetch_related("matched_schools__school")
            .order_by("-sitting__sitting_date", "-id")
        )


class SchoolMentionsView(ListAPIView):
    """List Hansard mentions for a school (excludes rejected)."""

    serializer_class = SchoolMentionSerializer
    authentication_classes = []
    permission_classes = []
    pagination_class = None

    def get_queryset(self):
        school = get_object_or_404(School, moe_code=self.kwargs["moe_code"])
        return (
            HansardMention.objects.filter(
                matched_schools__school=school,
            )
            .exclude(review_status="REJECTED")
            .select_related("sitting")
            .order_by("-sitting__sitting_date")
        )


class ConstituencyMentionsView(ListAPIView):
    """List Hansard mentions for a constituency's MP."""

    serializer_class = ConstituencyMentionSerializer
    authentication_classes = []
    permission_classes = []
    pagination_class = None

    def get_queryset(self):
        constituency = get_object_or_404(
            Constituency, code=self.kwargs["code"]
        )
        return (
            HansardMention.objects.filter(
                mp_constituency__icontains=constituency.name,
            )
            .exclude(review_status="REJECTED")
            .exclude(mp_name="")
            .select_related("sitting")
            .order_by("-sitting__sitting_date")
        )


class MeetingReportListView(ListAPIView):
    """List all parliamentary meetings with reports."""

    serializer_class = MeetingReportSerializer
    pagination_class = None

    def get_queryset(self):
        return (
            ParliamentaryMeeting.objects.exclude(report_html="")
            .annotate(
                _sitting_count=Count("sittings"),
                _total_mentions=Sum("sittings__mention_count"),
            )
            .order_by("-start_date")
        )


class MeetingReportDetailView(RetrieveAPIView):
    """Retrieve a single parliamentary meeting report."""

    serializer_class = MeetingReportSerializer

    def get_queryset(self):
        return ParliamentaryMeeting.objects.annotate(
            _sitting_count=Count("sittings"),
            _total_mentions=Sum("sittings__mention_count"),
        )


def meeting_illustration_view(request, pk):
    """Serve the meeting illustration as a PNG image."""
    meeting = get_object_or_404(ParliamentaryMeeting, pk=pk)
    if not meeting.illustration:
        return HttpResponse(status=404)
    return HttpResponse(
        bytes(meeting.illustration),
        content_type="image/png",
    )
