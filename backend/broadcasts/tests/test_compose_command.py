"""Tests for the compose_monthly_blast management command."""

from datetime import date, datetime
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from broadcasts.models import Broadcast
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
def sitting(db):
    return HansardSitting.objects.create(
        sitting_date=date(2026, 2, 10),
        pdf_url="https://example.com/feb.pdf",
        pdf_filename="feb.pdf",
        status=HansardSitting.Status.COMPLETED,
    )


@pytest.fixture
def mention(sitting):
    return HansardMention.objects.create(
        sitting=sitting,
        verbatim_quote="Tamil school test",
        mp_name="YB Test",
        significance=4,
        ai_summary="Parliament summary",
        review_status="APPROVED",
    )


@pytest.fixture
def article(db):
    return NewsArticle.objects.create(
        url="https://example.com/news-1",
        title="Tamil School News",
        source_name="The Star",
        body_text="Article body",
        status=NewsArticle.ANALYSED,
        relevance_score=4,
        sentiment=NewsArticle.POSITIVE,
        ai_summary="News summary",
        review_status=NewsArticle.APPROVED,
        published_date=timezone.make_aware(datetime(2026, 2, 15)),
    )


@pytest.fixture
def scorecard(constituency):
    return MPScorecard.objects.create(
        mp_name="YB Top",
        constituency=constituency,
        total_mentions=10,
        substantive_mentions=5,
    )


@pytest.mark.django_db
class TestComposeMonthlyBlast:
    """Tests for compose_monthly_blast management command."""

    def test_creates_draft_broadcast(self, mention, article, scorecard):
        out = StringIO()
        call_command("compose_monthly_blast", month="2026-02", stdout=out)
        assert Broadcast.objects.count() == 1
        broadcast = Broadcast.objects.first()
        assert broadcast.status == Broadcast.Status.DRAFT
        assert "February 2026" in broadcast.subject

    def test_broadcast_contains_parliament_content(self, mention):
        call_command("compose_monthly_blast", month="2026-02")
        broadcast = Broadcast.objects.first()
        assert "YB Test" in broadcast.html_content
        assert "Parliament Watch" in broadcast.html_content

    def test_broadcast_contains_news_content(self, article):
        call_command("compose_monthly_blast", month="2026-02")
        broadcast = Broadcast.objects.first()
        assert "Tamil School News" in broadcast.html_content
        assert "News Watch" in broadcast.html_content

    def test_broadcast_contains_scorecard_content(self, scorecard):
        call_command("compose_monthly_blast", month="2026-02")
        broadcast = Broadcast.objects.first()
        assert "YB Top" in broadcast.html_content
        assert "Scorecard" in broadcast.html_content

    def test_audience_filter_set_to_monthly_blast(self, mention):
        call_command("compose_monthly_blast", month="2026-02")
        broadcast = Broadcast.objects.first()
        assert broadcast.audience_filter == {"category": "MONTHLY_BLAST"}

    def test_dry_run_does_not_create_broadcast(self, mention):
        out = StringIO()
        call_command("compose_monthly_blast", month="2026-02", dry_run=True, stdout=out)
        assert Broadcast.objects.count() == 0
        output = out.getvalue()
        assert "DRY RUN" in output

    def test_dry_run_shows_counts(self, mention, article, scorecard):
        out = StringIO()
        call_command("compose_monthly_blast", month="2026-02", dry_run=True, stdout=out)
        output = out.getvalue()
        assert "1 parliament" in output
        assert "1 news" in output
        assert "1 scorecard" in output

    def test_defaults_to_previous_month(self, db):
        out = StringIO()
        call_command("compose_monthly_blast", stdout=out)
        assert Broadcast.objects.count() == 1

    def test_invalid_month_format_raises_error(self, db):
        with pytest.raises(CommandError, match="Invalid month format"):
            call_command("compose_monthly_blast", month="Feb-2026")

    def test_empty_month_still_creates_broadcast(self, db):
        call_command("compose_monthly_blast", month="2026-02")
        broadcast = Broadcast.objects.first()
        assert broadcast is not None
        assert "No intelligence data" in broadcast.html_content

    def test_subject_format(self, mention):
        call_command("compose_monthly_blast", month="2026-02")
        broadcast = Broadcast.objects.first()
        assert broadcast.subject == "Monthly Intelligence Blast \u2014 February 2026"

    def test_text_content_generated(self, mention):
        call_command("compose_monthly_blast", month="2026-02")
        broadcast = Broadcast.objects.first()
        assert broadcast.text_content != ""
        assert "Parliament Watch" in broadcast.text_content

    def test_prints_broadcast_id(self, mention):
        out = StringIO()
        call_command("compose_monthly_blast", month="2026-02", stdout=out)
        broadcast = Broadcast.objects.first()
        assert str(broadcast.pk) in out.getvalue()
