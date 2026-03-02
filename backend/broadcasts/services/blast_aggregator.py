"""
Aggregator service for the Monthly Intelligence Blast.

Queries approved HansardMentions, approved NewsArticles, and top
MPScorecards for a given month. Returns a dict with three keys
ready for template rendering.
"""

from hansard.models import HansardMention
from newswatch.models import NewsArticle
from parliament.models import MPScorecard


def aggregate_month(year: int, month: int) -> dict:
    """
    Aggregate top content for a given month.

    Returns:
        dict with keys:
        - parliament: up to 5 approved HansardMentions, by significance desc
        - news: up to 5 approved NewsArticles, by relevance_score desc
        - scorecards: up to 3 MPScorecards, by total_mentions desc
    """
    parliament = (
        HansardMention.objects.filter(
            sitting__sitting_date__year=year,
            sitting__sitting_date__month=month,
            review_status="APPROVED",
        )
        .exclude(mp_name="")
        .select_related("sitting")
        .order_by("-significance")[:5]
    )

    news = (
        NewsArticle.objects.filter(
            published_date__year=year,
            published_date__month=month,
            status=NewsArticle.ANALYSED,
            review_status=NewsArticle.APPROVED,
        )
        .order_by("-relevance_score")[:5]
    )

    scorecards = (
        MPScorecard.objects.select_related("constituency")
        .order_by("-total_mentions")[:3]
    )

    return {
        "parliament": parliament,
        "news": news,
        "scorecards": scorecards,
    }
