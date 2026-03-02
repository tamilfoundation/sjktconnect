"""Tests for the blast_aggregator service."""

from datetime import date, datetime

import pytest
from django.utils import timezone

from broadcasts.services.blast_aggregator import aggregate_month
from hansard.models import HansardMention, HansardSitting
from newswatch.models import NewsArticle
from parliament.models import MPScorecard
from schools.models import Constituency


@pytest.fixture
def constituency(db):
    return Constituency.objects.create(
        code="P001", name="Test Constituency", state="JOHOR"
    )


@pytest.fixture
def sitting_feb(db):
    return HansardSitting.objects.create(
        sitting_date=date(2026, 2, 10),
        pdf_url="https://example.com/feb.pdf",
        pdf_filename="feb.pdf",
        status=HansardSitting.Status.COMPLETED,
    )


@pytest.fixture
def sitting_jan(db):
    return HansardSitting.objects.create(
        sitting_date=date(2026, 1, 15),
        pdf_url="https://example.com/jan.pdf",
        pdf_filename="jan.pdf",
        status=HansardSitting.Status.COMPLETED,
    )


def _make_mention(sitting, significance, review_status="APPROVED", mp_name="MP Test"):
    return HansardMention.objects.create(
        sitting=sitting,
        verbatim_quote="Test quote",
        mp_name=mp_name,
        significance=significance,
        ai_summary="Summary text",
        review_status=review_status,
    )


def _make_article(title, relevance, review_status, published_date):
    return NewsArticle.objects.create(
        url=f"https://example.com/{title.replace(' ', '-')}",
        title=title,
        source_name="Test Source",
        body_text="Article body",
        status=NewsArticle.ANALYSED,
        relevance_score=relevance,
        sentiment=NewsArticle.POSITIVE,
        ai_summary="Article summary",
        review_status=review_status,
        published_date=published_date,
    )


@pytest.mark.django_db
class TestAggregateMonth:
    """Tests for aggregate_month()."""

    def test_empty_month_returns_empty_lists(self):
        result = aggregate_month(2026, 2)
        assert list(result["parliament"]) == []
        assert list(result["news"]) == []
        assert list(result["scorecards"]) == []

    def test_parliament_filters_by_month_and_approved(self, sitting_feb, sitting_jan):
        approved_feb = _make_mention(sitting_feb, 4, "APPROVED")
        _make_mention(sitting_feb, 3, "REJECTED")
        _make_mention(sitting_feb, 2, "PENDING")
        _make_mention(sitting_jan, 5, "APPROVED")

        result = aggregate_month(2026, 2)
        mentions = list(result["parliament"])
        assert len(mentions) == 1
        assert mentions[0].pk == approved_feb.pk

    def test_parliament_ordered_by_significance_desc(self, sitting_feb):
        low = _make_mention(sitting_feb, 2, "APPROVED", "MP Low")
        high = _make_mention(sitting_feb, 5, "APPROVED", "MP High")
        mid = _make_mention(sitting_feb, 3, "APPROVED", "MP Mid")

        result = aggregate_month(2026, 2)
        pks = [m.pk for m in result["parliament"]]
        assert pks == [high.pk, mid.pk, low.pk]

    def test_parliament_limited_to_5(self, sitting_feb):
        for i in range(7):
            _make_mention(sitting_feb, 5 - (i % 5), "APPROVED", f"MP {i}")

        result = aggregate_month(2026, 2)
        assert len(list(result["parliament"])) == 5

    def test_news_filters_by_month_and_approved(self, db):
        feb_date = timezone.make_aware(datetime(2026, 2, 15))
        jan_date = timezone.make_aware(datetime(2026, 1, 15))

        approved = _make_article("Good", 4, "APPROVED", feb_date)
        _make_article("Bad", 3, "REJECTED", feb_date)
        _make_article("Old", 5, "APPROVED", jan_date)

        result = aggregate_month(2026, 2)
        articles = list(result["news"])
        assert len(articles) == 1
        assert articles[0].pk == approved.pk

    def test_news_ordered_by_relevance_desc(self, db):
        feb = timezone.make_aware(datetime(2026, 2, 10))
        low = _make_article("Low", 2, "APPROVED", feb)
        high = _make_article("High", 5, "APPROVED", feb)

        result = aggregate_month(2026, 2)
        pks = [a.pk for a in result["news"]]
        assert pks == [high.pk, low.pk]

    def test_news_limited_to_5(self, db):
        feb = timezone.make_aware(datetime(2026, 2, 10))
        for i in range(7):
            _make_article(f"Article {i}", 3, "APPROVED", feb)

        result = aggregate_month(2026, 2)
        assert len(list(result["news"])) == 5

    def test_scorecards_ordered_by_total_mentions(self, constituency):
        low = MPScorecard.objects.create(
            mp_name="MP Low", constituency=constituency, total_mentions=2
        )
        high = MPScorecard.objects.create(
            mp_name="MP High", constituency=constituency, total_mentions=10
        )

        result = aggregate_month(2026, 2)
        pks = [s.pk for s in result["scorecards"]]
        assert pks == [high.pk, low.pk]

    def test_scorecards_limited_to_3(self, constituency):
        for i in range(5):
            MPScorecard.objects.create(
                mp_name=f"MP {i}", constituency=constituency, total_mentions=i
            )

        result = aggregate_month(2026, 2)
        assert len(list(result["scorecards"])) == 3

    def test_returns_dict_with_three_keys(self):
        result = aggregate_month(2026, 2)
        assert set(result.keys()) == {"parliament", "news", "scorecards"}
