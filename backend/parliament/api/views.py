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


def meeting_pdf_view(request, pk):
    """Serve a print-friendly branded HTML page for saving as PDF."""
    meeting = get_object_or_404(ParliamentaryMeeting, pk=pk)
    if not meeting.report_html:
        return HttpResponse(status=404)

    start_str = meeting.start_date.strftime("%d %B %Y")
    end_str = meeting.end_date.strftime("%d %B %Y")

    branded_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{meeting.short_name} — SJK(T) Connect Report</title>
<style>
    @page {{
        size: A4;
        margin: 2cm 2.5cm;
    }}
    @media print {{
        .no-print {{ display: none !important; }}
        body {{ font-size: 11px; }}
    }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                     Helvetica, Arial, sans-serif;
        font-size: 14px;
        line-height: 1.6;
        color: #1a1a1a;
        max-width: 800px;
        margin: 0 auto;
        padding: 20px;
    }}
    .brand-header {{
        border-bottom: 3px solid #1e40af;
        padding-bottom: 12px;
        margin-bottom: 24px;
    }}
    .brand-name {{
        font-size: 24px;
        font-weight: bold;
        color: #1e40af;
        margin: 0;
    }}
    .brand-tagline {{
        font-size: 12px;
        color: #6b7280;
        margin: 4px 0 0 0;
    }}
    .meeting-title {{
        font-size: 18px;
        font-weight: bold;
        color: #111827;
        margin: 20px 0 4px 0;
    }}
    .meeting-dates {{
        font-size: 13px;
        color: #6b7280;
        margin: 0 0 20px 0;
    }}
    h2 {{
        font-size: 16px;
        color: #1e40af;
        border-bottom: 1px solid #e5e7eb;
        padding-bottom: 4px;
        margin-top: 24px;
        margin-bottom: 10px;
    }}
    h3 {{
        font-size: 14px;
        color: #374151;
        margin-top: 16px;
        margin-bottom: 8px;
    }}
    p {{ margin: 8px 0; }}
    ul {{ margin: 8px 0; padding-left: 24px; }}
    li {{ margin: 4px 0; }}
    table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 12px;
        margin: 12px 0;
    }}
    th {{
        background-color: #f3f4f6;
        border: 1px solid #d1d5db;
        padding: 6px 10px;
        text-align: left;
        font-weight: bold;
    }}
    td {{
        border: 1px solid #e5e7eb;
        padding: 6px 10px;
    }}
    a {{ color: #1e40af; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .footer {{
        margin-top: 40px;
        padding-top: 12px;
        border-top: 1px solid #e5e7eb;
        font-size: 11px;
        color: #9ca3af;
        text-align: center;
    }}
    .print-btn {{
        position: fixed;
        top: 16px;
        right: 16px;
        background: #1e40af;
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
    }}
    .print-btn:hover {{ background: #1e3a8a; }}
</style>
</head>
<body>
    <button class="print-btn no-print" onclick="window.print()">
        Save as PDF
    </button>
    <div class="brand-header">
        <p class="brand-name">SJK(T) Connect</p>
        <p class="brand-tagline">
            Tamil School Intelligence &amp; Advocacy &bull; tamilschool.org
        </p>
    </div>
    <p class="meeting-title">{meeting.short_name}</p>
    <p class="meeting-dates">{start_str} &ndash; {end_str}</p>
    {meeting.report_html}
    <div class="footer">
        Generated by SJK(T) Connect &bull; tamilschool.org &bull;
        Data sourced from Malaysian Parliament Hansard
    </div>
</body>
</html>"""

    return HttpResponse(branded_html, content_type="text/html")
