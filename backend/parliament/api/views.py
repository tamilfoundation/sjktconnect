"""API views for MPScorecard and SittingBrief."""

from rest_framework.generics import ListAPIView, RetrieveAPIView

from parliament.api.serializers import MPScorecardSerializer, SittingBriefSerializer
from parliament.models import MPScorecard, SittingBrief


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
