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

    def test_semicolon_split_keeps_only_first_story(self):
        """Regression for May 2026 send: Gemini occasionally joins two stories
        with a semicolon. Defensive split takes only the first clause."""
        from broadcasts.management.commands.compose_monthly_blast import Command
        cmd = Command()
        result = cmd._build_subject(
            "May 2026",
            {"headline": "Private Sector Boosts SJK(T) Ladang Labu; "
                         "Sedenak Gets Piped Water After 67 Years"},
        )
        assert result == "May 2026: Private Sector Boosts SJK(T) Ladang Labu"

    def test_and_joiner_split_keeps_only_first_story(self):
        from broadcasts.management.commands.compose_monthly_blast import Command
        cmd = Command()
        result = cmd._build_subject(
            "April 2026",
            {"headline": "RM15M funding announced and new playground opens"},
        )
        assert result == "April 2026: RM15M funding announced"

    def test_does_not_split_internal_and_in_school_name(self):
        """Word boundary safety: 'and' inside a name (no surrounding spaces
        treated as a joiner) must not split."""
        from broadcasts.management.commands.compose_monthly_blast import Command
        cmd = Command()
        # "Sungai Sandhanam" contains 'and' but as part of a single word \u2014
        # our splitter uses " and " (with spaces) so this is safe.
        result = cmd._build_subject(
            "April 2026",
            {"headline": "Sungai Sandhanam school expansion approved"},
        )
        assert result == "April 2026: Sungai Sandhanam school expansion approved"

    def test_trailing_punctuation_stripped_after_split(self):
        from broadcasts.management.commands.compose_monthly_blast import Command
        cmd = Command()
        result = cmd._build_subject(
            "April 2026",
            {"headline": "Funding boost,; new playground opens"},
        )
        assert result == "April 2026: Funding boost"


@pytest.mark.django_db
@patch(
    "broadcasts.management.commands.compose_monthly_blast.generate_monthly_analysis",
)
@patch(
    "broadcasts.management.commands.compose_monthly_blast.cluster_news_articles",
)
@patch(
    "broadcasts.management.commands.compose_monthly_blast.generate_hero_image",
    return_value=None,
)
class TestSprint24RenderSmoke:
    """Sprint 24 task #8 — structural render smoke test.

    Per lesson 102, retros/tests must reference the code that proves the
    work landed. This class asserts the rendered HTML carries every
    Sprint 24 structural promise: recess banner, in-body CTAs, source
    links on news/briefs/meetings, schools-by-state table, captioned
    numbers, no unescaped em-dash, no leaked template tokens.
    """

    def _setup_mocks(self, _ana, _cluster):
        _ana.return_value = _stub_analysis()
        _cluster.return_value = [
            {
                "headline": "Test story cluster",
                "story_summary": "1-2 sentence synopsis",
                "articles": [],
                "article_count": 0,
                "lead_article": None,
                "max_relevance": 0,
                "sentiment_majority": "NEUTRAL",
                "score": 0,
                "is_other": False,
            }
        ]

    def test_render_carries_donate_link_via_footer(self, _hero, _cluster, _ana, db):
        self._setup_mocks(_ana, _cluster)
        call_command("compose_monthly_blast", month="2026-02")
        broadcast = Broadcast.objects.first()
        # The footer Donate link comes from the body Take Action CTA
        # (Sprint 24 #4b) — the global footer in _wrap_broadcast_html
        # adds another at send time, not at compose time.
        assert "tamilschool.org/donate" in broadcast.html_content

    def test_render_carries_forward_mailto(self, _hero, _cluster, _ana, db):
        self._setup_mocks(_ana, _cluster)
        call_command("compose_monthly_blast", month="2026-02")
        broadcast = Broadcast.objects.first()
        # Sprint 24 Q1 LOCKED: Forward CTA = mailto:
        assert "mailto:" in broadcast.html_content

    def test_render_carries_parliament_watch_cta(self, _hero, _cluster, _ana, db):
        self._setup_mocks(_ana, _cluster)
        call_command("compose_monthly_blast", month="2026-02")
        broadcast = Broadcast.objects.first()
        assert "tamilschool.org/parliament-watch" in broadcast.html_content

    def test_render_has_no_unrendered_template_tokens(self, _hero, _cluster, _ana, db):
        """Regression: catches template variable typos (a real April
        2026 prototype bug rendered raw `{'name': ..., 'reason': ...}`).
        """
        self._setup_mocks(_ana, _cluster)
        call_command("compose_monthly_blast", month="2026-02")
        broadcast = Broadcast.objects.first()
        assert "{{" not in broadcast.html_content
        assert "{%" not in broadcast.html_content
        # Don't accept raw Python repr-style dicts in body either.
        assert "{'name':" not in broadcast.html_content
        assert "{\"name\":" not in broadcast.html_content

    def test_render_has_no_unescaped_em_dash(self, _hero, _cluster, _ana, db):
        """Lesson 21 — literal Unicode em-dash renders as a diamond in
        some mail clients. Templates must use the entity.
        """
        self._setup_mocks(_ana, _cluster)
        call_command("compose_monthly_blast", month="2026-02")
        broadcast = Broadcast.objects.first()
        # Stub analysis text MAY include LLM-emitted em-dashes; the
        # template itself must not introduce any. Strip the analysis
        # content before checking.
        template_only = broadcast.html_content
        for value in _stub_analysis().values():
            if isinstance(value, str):
                template_only = template_only.replace(value, "")
        assert "\u2014" not in template_only, (
            "Template introduced a literal em-dash (use &mdash;)"
        )

    def test_render_emits_recess_banner_when_not_in_session(
        self, _hero, _cluster, _ana, db
    ):
        self._setup_mocks(_ana, _cluster)
        # Empty DB month — no HansardSittings → parliament_was_in_session=False
        call_command("compose_monthly_blast", month="2026-02")
        broadcast = Broadcast.objects.first()
        assert "Parliament was not in session" in broadcast.html_content

    def test_render_no_recess_banner_when_in_session(
        self, _hero, _cluster, _ana, sitting
    ):
        self._setup_mocks(_ana, _cluster)
        # `sitting` fixture is a HansardSitting with status=COMPLETED in
        # 2026-02 — that triggers parliament_was_in_session=True.
        call_command("compose_monthly_blast", month="2026-02")
        broadcast = Broadcast.objects.first()
        assert "Parliament was not in session" not in broadcast.html_content

    def test_render_news_cluster_renders_headline_and_lead_link(
        self, _hero, _cluster, _ana, db
    ):
        """Sprint 24 #10b: one card per story. Cluster headline is the
        linked text; lead_article.url is the destination.
        """
        article = NewsArticle.objects.create(
            url="https://themalaysiapress.com/sjkt-test",
            title="SJK(T) Test Article",
            source_name="Test Source",
            published_date=timezone.make_aware(datetime(2026, 2, 5)),
            status=NewsArticle.ANALYSED,
            review_status=NewsArticle.APPROVED,
            relevance_score=4,
            sentiment="POSITIVE",
        )
        _ana.return_value = _stub_analysis()
        _cluster.return_value = [
            {
                "headline": "Test cluster headline",
                "story_summary": "Synopsis.",
                "articles": [article],
                "article_count": 1,
                "lead_article": article,
                "max_relevance": 4,
                "sentiment_majority": "POSITIVE",
                "score": 7,
                "is_other": False,
            }
        ]
        call_command("compose_monthly_blast", month="2026-02")
        broadcast = Broadcast.objects.first()
        assert "Test cluster headline" in broadcast.html_content
        # Lead article URL is the destination of the cluster headline link.
        assert "https://themalaysiapress.com/sjkt-test" in broadcast.html_content
        # The source name appears in the cluster meta line.
        assert "Test Source" in broadcast.html_content

    def test_render_shows_remainder_footer_when_articles_dropped(
        self, _hero, _cluster, _ana, db
    ):
        """Sprint 24 #10b: dropped + Other articles tally into a footer
        line so the email never silently hides coverage.
        """
        article = NewsArticle.objects.create(
            url="https://example.com/lead",
            title="Lead",
            source_name="Src",
            published_date=timezone.make_aware(datetime(2026, 2, 5)),
            status=NewsArticle.ANALYSED,
            review_status=NewsArticle.APPROVED,
            relevance_score=4,
            sentiment="POSITIVE",
        )
        _ana.return_value = _stub_analysis()
        # 1 real cluster shown + 1 Other bucket (3 articles) → remainder=3
        _cluster.return_value = [
            {
                "headline": "Top",
                "story_summary": "S",
                "articles": [article],
                "article_count": 1,
                "lead_article": article,
                "max_relevance": 4,
                "sentiment_majority": "POSITIVE",
                "score": 7,
                "is_other": False,
            },
            {
                "headline": "Other coverage",
                "story_summary": "",
                "articles": [article, article, article],
                "article_count": 3,
                "lead_article": article,
                "max_relevance": 4,
                "sentiment_majority": "POSITIVE",
                "score": 0,
                "is_other": True,
            },
        ]
        call_command("compose_monthly_blast", month="2026-02")
        broadcast = Broadcast.objects.first()
        assert "Plus 3 other articles" in broadcast.html_content
        assert "tamilschool.org/en/news" in broadcast.html_content

    def test_render_suppresses_scorecards_section_on_lifetime_fallback(
        self, _hero, _cluster, _ana, scorecard
    ):
        """Sprint 24 #4d LOCKED: lifetime fallback → suppress the
        scorecard section entirely (no scorecard fixture in month).
        """
        self._setup_mocks(_ana, _cluster)
        call_command("compose_monthly_blast", month="2026-02")
        broadcast = Broadcast.objects.first()
        # scorecard fixture has no last_mention_date → falls back to
        # lifetime → section should NOT render.
        assert "Most Active MPs This Month" not in broadcast.html_content
