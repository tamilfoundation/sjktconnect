"""Tests for the compose_monthly_blast management command."""

from datetime import date, datetime
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from broadcasts.models import Broadcast
from hansard.models import HansardMention, HansardSitting
from newswatch.models import NewsArticle
from parliament.models import MPScorecard
from schools.models import Constituency


def _stub_analysis():
    """Stub for generate_monthly_analysis used across compose tests.

    Sprint 24 #6 (LOCKED 2026-05-11): the v1 template was removed, so
    every compose path requires Gemini to return a valid analysis dict.
    These tests don't exercise Gemini itself — that's covered in
    test_monthly_analyst.py — so we return a fixed stub and assert
    against its content where applicable.
    """
    return {
        "executive_summary": (
            "This month saw significant developments across Parliament Watch, "
            "News Watch, and Scorecard tracking."
        ),
        "trend_lines": [
            {"trend": "Test trend", "direction": "up", "detail": "Up 10%."}
        ],
        "emerging_signals": ["Test signal."],
        "fading_from_view": [],
        "opportunity_watch": ["Test opportunity."],
        "school_spotlight": None,
        "headline": "",
        "by_the_numbers": {
            "parliament_mentions": 1,
            "news_articles": 1,
            "schools_affected": 1,
            "sentiment_positive": 1,
            "sentiment_negative": 0,
        },
    }


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
@patch(
    "broadcasts.management.commands.compose_monthly_blast.generate_monthly_analysis",
    return_value=_stub_analysis(),
)
@patch(
    "broadcasts.management.commands.compose_monthly_blast.cluster_news_articles",
    return_value=[],
)
@patch(
    "broadcasts.management.commands.compose_monthly_blast.generate_hero_image",
    return_value=None,
)
class TestComposeMonthlyBlast:
    """Tests for compose_monthly_blast management command.

    Sprint 24 #6 LOCKED: v1 fallback removed. Every test mocks
    generate_monthly_analysis to return a valid stub so the new
    abort-on-None path doesn't fire. Gemini behaviour is covered in
    test_monthly_analyst.py and test_topic_clusterer.py.
    """

    def test_creates_draft_broadcast(self, _hero, _cluster, _ana, mention, article, scorecard):
        out = StringIO()
        call_command("compose_monthly_blast", month="2026-02", stdout=out)
        assert Broadcast.objects.count() == 1
        broadcast = Broadcast.objects.first()
        assert broadcast.status == Broadcast.Status.DRAFT
        assert "February 2026" in broadcast.subject

    def test_broadcast_contains_parliament_content(self, _hero, _cluster, _ana, mention):
        call_command("compose_monthly_blast", month="2026-02")
        broadcast = Broadcast.objects.first()
        # v2 template renders LLM analysis content; the stub mentions
        # Parliament Watch in executive_summary so the keyword appears.
        # Raw mention rendering (YB Test) lands in Task 4 (template
        # overhaul) — re-assert there.
        assert "Parliament Watch" in broadcast.html_content

    def test_broadcast_contains_news_content(self, _hero, _cluster, _ana, article):
        call_command("compose_monthly_blast", month="2026-02")
        broadcast = Broadcast.objects.first()
        # Stub mentions "News Watch" in executive_summary; raw article
        # titles will appear after Task 5 (news cards inline).
        assert "News Watch" in broadcast.html_content

    def test_broadcast_contains_scorecard_content(self, _hero, _cluster, _ana, scorecard):
        call_command("compose_monthly_blast", month="2026-02")
        broadcast = Broadcast.objects.first()
        # Stub mentions "Scorecard" in executive_summary. Raw scorecard
        # rendering is Task 4's call (suppress-or-reframe lifetime
        # fallback) — re-assert there.
        assert "Scorecard" in broadcast.html_content

    def test_audience_filter_set_to_monthly_blast(self, _hero, _cluster, _ana, mention):
        call_command("compose_monthly_blast", month="2026-02")
        broadcast = Broadcast.objects.first()
        assert broadcast.audience_filter == {"category": "MONTHLY_BLAST"}

    def test_dry_run_does_not_create_broadcast(self, _hero, _cluster, _ana, mention):
        out = StringIO()
        call_command("compose_monthly_blast", month="2026-02", dry_run=True, stdout=out)
        assert Broadcast.objects.count() == 0
        output = out.getvalue()
        assert "DRY RUN" in output

    def test_dry_run_shows_counts(self, _hero, _cluster, _ana, mention, article, scorecard):
        out = StringIO()
        call_command("compose_monthly_blast", month="2026-02", dry_run=True, stdout=out)
        output = out.getvalue()
        # Sprint 23 dry-run output uses the long-form counts.
        assert "1 mentions total" in output
        assert "1 approved" in output
        assert "1 scorecard items" in output

    def test_defaults_to_previous_month(self, _hero, _cluster, _ana, db):
        out = StringIO()
        call_command("compose_monthly_blast", stdout=out)
        assert Broadcast.objects.count() == 1

    def test_invalid_month_format_raises_error(self, _hero, _cluster, _ana, db):
        with pytest.raises(CommandError, match="Invalid month format"):
            call_command("compose_monthly_blast", month="Feb-2026")

    def test_invalid_backfill_since_raises_error(self, _hero, _cluster, _ana, db):
        # Sprint 18 — guard the new flag's parsing.
        with pytest.raises(CommandError, match="Invalid --backfill-since"):
            call_command(
                "compose_monthly_blast",
                month="2026-02",
                backfill_since="not-a-date",
                dry_run=True,
            )

    def test_dry_run_with_backfill_since_runs(self, _hero, _cluster, _ana, db):
        # Sprint 18 — flag is accepted; aggregator widens the brief +
        # meeting window. Empty DB → counts are 0 but the run completes
        # and reports the backfill window in the output.
        out = StringIO()
        call_command(
            "compose_monthly_blast",
            month="2026-02",
            backfill_since="2026-01-01",
            dry_run=True,
            stdout=out,
        )
        output = out.getvalue()
        assert "backfill window: items >= 2026-01-01" in output

    def test_empty_month_still_creates_broadcast(self, _hero, _cluster, _ana, db):
        # Sprint 18 note: data migration 0003_seed_meetings creates
        # ParliamentaryMeeting rows that overlap most months in
        # 2025-2026; the command still creates a Broadcast row even
        # with sparse content.
        call_command("compose_monthly_blast", month="2026-02")
        broadcast = Broadcast.objects.first()
        assert broadcast is not None
        assert broadcast.subject == "Monthly Intelligence Blast \u2014 February 2026"

    def test_subject_format(self, _hero, _cluster, _ana, mention):
        call_command("compose_monthly_blast", month="2026-02")
        broadcast = Broadcast.objects.first()
        assert broadcast.subject == "Monthly Intelligence Blast \u2014 February 2026"

    def test_text_content_generated(self, _hero, _cluster, _ana, mention):
        call_command("compose_monthly_blast", month="2026-02")
        broadcast = Broadcast.objects.first()
        assert broadcast.text_content != ""
        assert "Parliament Watch" in broadcast.text_content

    def test_prints_broadcast_id(self, _hero, _cluster, _ana, mention):
        out = StringIO()
        call_command("compose_monthly_blast", month="2026-02", stdout=out)
        broadcast = Broadcast.objects.first()
        assert str(broadcast.pk) in out.getvalue()

    def test_aborts_when_analyst_returns_none(self, _hero, _cluster, _ana, db):
        """Sprint 24 #6 LOCKED: no v1 fallback. Gemini-unavailable
        becomes a clean CommandError with an ops-friendly message.
        """
        _ana.return_value = None
        with pytest.raises(CommandError, match="Sprint 24 removed the"):
            call_command("compose_monthly_blast", month="2026-02")
        assert Broadcast.objects.count() == 0


class TestSprint23DynamicSubject:
    """Sprint 23: subject line uses LLM-generated headline when available."""

    def test_falls_back_to_generic_when_no_analysis(self):
        from broadcasts.management.commands.compose_monthly_blast import Command
        cmd = Command()
        result = cmd._build_subject("April 2026", None)
        assert result == "Monthly Intelligence Blast \u2014 April 2026"

    def test_falls_back_when_headline_missing(self):
        from broadcasts.management.commands.compose_monthly_blast import Command
        cmd = Command()
        result = cmd._build_subject(
            "April 2026",
            {"executive_summary": "x", "trend_lines": []},
        )
        assert result == "Monthly Intelligence Blast \u2014 April 2026"

    def test_falls_back_when_headline_empty_string(self):
        from broadcasts.management.commands.compose_monthly_blast import Command
        cmd = Command()
        result = cmd._build_subject("April 2026", {"headline": "   "})
        assert result == "Monthly Intelligence Blast \u2014 April 2026"

    def test_uses_llm_headline_when_present(self):
        from broadcasts.management.commands.compose_monthly_blast import Command
        cmd = Command()
        result = cmd._build_subject(
            "April 2026",
            {"headline": "Special ed coming to Tamil schools in 2027"},
        )
        assert result == "April 2026: Special ed coming to Tamil schools in 2027"

    def test_truncates_overlong_headline(self):
        from broadcasts.management.commands.compose_monthly_blast import Command
        cmd = Command()
        very_long = "x" * 200
        result = cmd._build_subject("April 2026", {"headline": very_long})
        assert len(result) <= 90
        assert result.endswith("\u2026")  # ellipsis
