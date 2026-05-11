"""Tests for the blast_aggregator service.

Sprint 18 rewrote this test file:
  - Mention filter changed from review_status=APPROVED to
    exclude(REJECTED). PENDING items now appear (they default to
    PENDING and were silently dropped by the prior filter — the bug
    that hid 3 mentions from the 1 Apr 2026 monthly digest).
  - aggregate_month() now also returns 'briefs' and 'meeting_reports'
    keys, plus 'scorecards_are_lifetime_fallback' bool.
  - --backfill-since semantics added for briefs + meeting_reports.
"""

from datetime import date, datetime

import pytest
from django.utils import timezone

from broadcasts.services.blast_aggregator import aggregate_month
from hansard.models import HansardMention, HansardSitting
from newswatch.models import NewsArticle
from parliament.models import (
    MPScorecard,
    ParliamentaryMeeting,
    SittingBrief,
)
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


@pytest.fixture
def sitting_mar(db):
    return HansardSitting.objects.create(
        sitting_date=date(2026, 3, 2),
        pdf_url="https://example.com/mar.pdf",
        pdf_filename="mar.pdf",
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


def _make_brief(sitting, title="Test Brief", is_published=True):
    return SittingBrief.objects.create(
        sitting=sitting,
        title=title,
        summary_html="<p>Summary</p>",
        is_published=is_published,
    )


_meeting_counter = {"n": 0}


def _make_meeting(short_name, start, end, *, is_published=True, published_at=None):
    """Auto-allocates a unique (term, session, year) triple per call so
    tests can create multiple meetings without colliding on the model's
    unique_together constraint. Bumps all three fields so collisions are
    impossible regardless of test isolation behaviour.
    """
    _meeting_counter["n"] += 1
    n = _meeting_counter["n"]
    return ParliamentaryMeeting.objects.create(
        name=f"{short_name} Long Name",
        short_name=short_name,
        term=n,
        session=n,
        year=2000 + n,  # arbitrary, just unique
        start_date=start,
        end_date=end,
        is_published=is_published,
        published_at=published_at,
    )


@pytest.mark.django_db
class TestAggregateMonthMentions:
    """Mention filter — Sprint 18 changed APPROVED → exclude(REJECTED)."""

    def test_pending_mentions_are_included(self, sitting_feb):
        # Sprint 18: this was the actual bug. Default review_status is
        # PENDING; the public site shows them; the digest used to drop
        # them. Now the digest sees them too.
        m = _make_mention(sitting_feb, 4, "PENDING")
        result = aggregate_month(2026, 2)
        assert m in list(result["parliament"])

    def test_rejected_mentions_are_excluded(self, sitting_feb):
        _make_mention(sitting_feb, 4, "REJECTED")
        result = aggregate_month(2026, 2)
        assert list(result["parliament"]) == []

    def test_approved_mentions_still_included(self, sitting_feb):
        m = _make_mention(sitting_feb, 4, "APPROVED")
        result = aggregate_month(2026, 2)
        assert m in list(result["parliament"])

    def test_filters_by_sitting_month(self, sitting_feb, sitting_jan):
        feb_mention = _make_mention(sitting_feb, 4, "APPROVED", "MP Feb")
        _make_mention(sitting_jan, 5, "APPROVED", "MP Jan")
        result = aggregate_month(2026, 2)
        assert [m.pk for m in result["parliament"]] == [feb_mention.pk]

    def test_ordered_by_significance_desc(self, sitting_feb):
        low = _make_mention(sitting_feb, 2, "APPROVED", "MP Low")
        high = _make_mention(sitting_feb, 5, "APPROVED", "MP High")
        mid = _make_mention(sitting_feb, 3, "APPROVED", "MP Mid")
        result = aggregate_month(2026, 2)
        assert [m.pk for m in result["parliament"]] == [high.pk, mid.pk, low.pk]

    def test_limited_to_5(self, sitting_feb):
        for i in range(7):
            _make_mention(sitting_feb, 5 - (i % 5), "APPROVED", f"MP {i}")
        result = aggregate_month(2026, 2)
        assert len(list(result["parliament"])) == 5

    def test_blank_mp_name_excluded(self, sitting_feb):
        _make_mention(sitting_feb, 5, "APPROVED", mp_name="")
        result = aggregate_month(2026, 2)
        assert list(result["parliament"]) == []


@pytest.mark.django_db
class TestAggregateMonthNews:
    """News still requires APPROVED (the editorial workflow sets it)."""

    def test_filters_by_month_and_approved(self, db):
        feb_date = timezone.make_aware(datetime(2026, 2, 15))
        jan_date = timezone.make_aware(datetime(2026, 1, 15))

        approved = _make_article("Good", 4, "APPROVED", feb_date)
        _make_article("Bad", 3, "REJECTED", feb_date)
        _make_article("Old", 5, "APPROVED", jan_date)

        result = aggregate_month(2026, 2)
        articles = list(result["news"])
        assert [a.pk for a in articles] == [approved.pk]

    def test_ordered_by_relevance_desc(self, db):
        feb = timezone.make_aware(datetime(2026, 2, 10))
        low = _make_article("Low", 2, "APPROVED", feb)
        high = _make_article("High", 5, "APPROVED", feb)
        result = aggregate_month(2026, 2)
        assert [a.pk for a in result["news"]] == [high.pk, low.pk]

    def test_limited_to_5(self, db):
        feb = timezone.make_aware(datetime(2026, 2, 10))
        for i in range(7):
            _make_article(f"Article {i}", 3, "APPROVED", feb)
        result = aggregate_month(2026, 2)
        assert len(list(result["news"])) == 5


@pytest.mark.django_db
class TestAggregateMonthBriefs:
    """Sprint 18 — sitting briefs included in aggregator output."""

    def test_brief_in_target_month_included(self, sitting_feb):
        b = _make_brief(sitting_feb, "Feb brief")
        result = aggregate_month(2026, 2)
        assert b in list(result["briefs"])

    def test_brief_outside_month_excluded(self, sitting_jan):
        _make_brief(sitting_jan, "Jan brief")
        result = aggregate_month(2026, 2)
        assert list(result["briefs"]) == []

    def test_unpublished_brief_still_included(self, sitting_feb):
        # Sprint 18 dry-run finding: prod data routinely has
        # is_published=False on briefs that ARE shown on the public
        # site (the parliament/api endpoints don't filter on the
        # flag). Aggregator must mirror public visibility, so it
        # also doesn't filter on is_published.
        b = _make_brief(sitting_feb, "Draft brief", is_published=False)
        result = aggregate_month(2026, 2)
        assert b in list(result["briefs"])

    def test_backfill_includes_older_briefs(self, sitting_jan, sitting_feb):
        # The whole point of --backfill-since: a digest that missed the
        # Jan brief should be able to catch up by widening the window.
        jan_brief = _make_brief(sitting_jan, "Jan brief")
        feb_brief = _make_brief(sitting_feb, "Feb brief")
        result = aggregate_month(2026, 2, backfill_since=date(2026, 1, 1))
        pks = {b.pk for b in result["briefs"]}
        assert pks == {jan_brief.pk, feb_brief.pk}

    def test_backfill_does_not_pull_pre_window_briefs(self, sitting_jan, sitting_feb):
        # backfill_since should be inclusive of items >= that date but
        # not earlier ones.
        old_sitting = HansardSitting.objects.create(
            sitting_date=date(2025, 12, 1),
            pdf_url="x", pdf_filename="x.pdf",
        )
        _make_brief(old_sitting, "Old brief")
        feb_brief = _make_brief(sitting_feb, "Feb brief")
        result = aggregate_month(2026, 2, backfill_since=date(2026, 1, 1))
        assert [b.pk for b in result["briefs"]] == [feb_brief.pk]


@pytest.mark.django_db
class TestAggregateMonthMeetingReports:
    """Sprint 18 — meeting reports included via overlap filter."""

    def test_meeting_overlapping_target_month_included(self, db):
        # Meeting runs 19 Jan -> 03 Mar. For Feb digest, this should
        # appear because it's "active" during Feb.
        m = _make_meeting("1st Mtg 2026", date(2026, 1, 19), date(2026, 3, 3))
        result = aggregate_month(2026, 2)
        assert m in list(result["meeting_reports"])

    def test_meeting_starting_in_target_month_included(self, db):
        m = _make_meeting("Feb mtg", date(2026, 2, 5), date(2026, 2, 28))
        result = aggregate_month(2026, 2)
        assert m in list(result["meeting_reports"])

    def test_meeting_ending_in_target_month_included(self, db):
        m = _make_meeting("Late Feb end", date(2026, 1, 1), date(2026, 2, 5))
        result = aggregate_month(2026, 2)
        assert m in list(result["meeting_reports"])

    def test_meeting_entirely_outside_excluded(self, db):
        # Note: data migration 0003_seed_meetings creates real meetings
        # (1st Mtg 2026, etc.) so we assert that OUR fixtures are
        # absent rather than that the result is globally empty.
        pre = _make_meeting("Pre-target", date(2025, 11, 1), date(2025, 12, 1))
        post = _make_meeting("Post-target", date(2026, 5, 1), date(2026, 6, 1))
        result = aggregate_month(2026, 2)
        meetings = list(result["meeting_reports"])
        assert pre not in meetings
        assert post not in meetings

    def test_unpublished_meeting_still_included(self, db):
        # Sprint 18: same rationale as briefs — aggregator mirrors
        # public-site visibility (no is_published filter).
        m = _make_meeting("Draft", date(2026, 2, 1), date(2026, 2, 28), is_published=False)
        result = aggregate_month(2026, 2)
        assert m in list(result["meeting_reports"])

    def test_backfill_window_picks_up_concluded_meetings(self, db):
        # The 1st Meeting 2026 case: meeting ended 03 Mar; April
        # digest (target month = Apr) won't see it via overlap. With
        # backfill_since=01 Mar, the end_date falls in the backfill
        # window and the meeting appears. Sprint 18 switched from
        # published_at to end_date because prod data routinely has
        # published_at=None.
        m = _make_meeting(
            "1st Mtg 2026",
            date(2026, 1, 19),
            date(2026, 3, 3),
        )
        result = aggregate_month(2026, 4, backfill_since=date(2026, 3, 1))
        assert m in list(result["meeting_reports"])

    def test_backfill_does_not_double_count(self, db):
        # A meeting that overlaps the target month AND ends within
        # the backfill window should appear exactly once.
        m = _make_meeting(
            "Overlapping mtg",
            date(2026, 2, 1),
            date(2026, 2, 28),
        )
        result = aggregate_month(2026, 2, backfill_since=date(2026, 1, 1))
        meetings = list(result["meeting_reports"])
        assert meetings.count(m) == 1


@pytest.mark.django_db
class TestAggregateMonthScorecards:
    """Sprint 18 — scorecards date-filtered, lifetime fallback when empty."""

    def test_scorecard_active_this_month_included(self, constituency):
        active = MPScorecard.objects.create(
            mp_name="MP Active", constituency=constituency,
            total_mentions=5, last_mention_date=date(2026, 2, 10),
        )
        result = aggregate_month(2026, 2)
        assert active in list(result["scorecards"])
        assert result["scorecards_are_lifetime_fallback"] is False

    def test_scorecard_inactive_this_month_falls_back_to_lifetime(self, constituency):
        # Old activity but still in the lifetime top-3 — appears as
        # the fallback rather than leaving the section blank.
        old = MPScorecard.objects.create(
            mp_name="MP Old", constituency=constituency,
            total_mentions=10, last_mention_date=date(2025, 11, 1),
        )
        result = aggregate_month(2026, 2)
        assert old in list(result["scorecards"])
        assert result["scorecards_are_lifetime_fallback"] is True

    def test_active_this_month_preferred_over_inactive_higher_scorer(self, constituency):
        MPScorecard.objects.create(
            mp_name="MP Old Big", constituency=constituency,
            total_mentions=100, last_mention_date=date(2025, 11, 1),
        )
        active = MPScorecard.objects.create(
            mp_name="MP Active Small", constituency=constituency,
            total_mentions=2, last_mention_date=date(2026, 2, 10),
        )
        result = aggregate_month(2026, 2)
        assert [s.pk for s in result["scorecards"]] == [active.pk]
        assert result["scorecards_are_lifetime_fallback"] is False

    def test_limited_to_3(self, constituency):
        for i in range(5):
            MPScorecard.objects.create(
                mp_name=f"MP {i}", constituency=constituency,
                total_mentions=i, last_mention_date=date(2026, 2, 1),
            )
        result = aggregate_month(2026, 2)
        assert len(list(result["scorecards"])) == 3


@pytest.mark.django_db
class TestAggregateMonthShape:
    """Result dict structure (Sprint 18 expanded keys, Sprint 23 added counts)."""

    def test_returns_dict_with_expected_keys(self):
        result = aggregate_month(2026, 2)
        assert set(result.keys()) == {
            # Sprint 18 keys (display-capped samples)
            "parliament",
            "news",
            "briefs",
            "meeting_reports",
            "scorecards",
            "scorecards_are_lifetime_fallback",
            # Sprint 23 keys (deterministic counts + visibility lists)
            "parliament_total",
            "news_total",
            "news_all",
            "news_sentiment_breakdown",
            "schools_mentioned",
            "schools_mentioned_total",
            "parliament_was_in_session",
            "parliament_sitting_count",
        }

    def test_empty_month_returns_expected_collection_types(self):
        # Cannot assert empty because data migration 0003_seed_meetings
        # seeds real ParliamentaryMeeting rows on test DB setup. The
        # invariant we CAN test is that the result has the right shape
        # (collections + the lifetime-fallback bool).
        result = aggregate_month(2026, 2)
        assert list(result["parliament"]) == []
        assert list(result["news"]) == []
        assert list(result["briefs"]) == []
        assert list(result["scorecards"]) == []
        assert result["scorecards_are_lifetime_fallback"] is True
        # meeting_reports may be non-empty due to seeded data — just
        # verify the field exists and is iterable.
        assert hasattr(result["meeting_reports"], "__iter__")
        # Sprint 23 deterministic counts default to 0 for an empty month
        assert result["parliament_total"] == 0
        assert result["news_total"] == 0
        assert result["news_sentiment_breakdown"] == {
            "positive": 0, "negative": 0, "neutral": 0,
        }
        assert result["schools_mentioned"] == []
        assert result["schools_mentioned_total"] == 0
        assert result["parliament_was_in_session"] is False
        assert result["parliament_sitting_count"] == 0


class TestSprint23DeterministicCounts:
    """Sprint 23: headline numbers must come from real DB counts, not
    the length of a display-capped sample."""

    def test_news_total_is_full_count_not_capped_sample(self, db):
        """Aggregator caps `news` at 5 for narrative; `news_total` must
        report the FULL approved count regardless of the cap."""
        from newswatch.models import NewsArticle
        from datetime import date as _date
        for i in range(8):
            NewsArticle.objects.create(
                url=f"https://example.com/a{i}",
                title=f"Article {i}",
                published_date=_date(2026, 2, 15),
                status=NewsArticle.ANALYSED,
                review_status=NewsArticle.APPROVED,
                relevance_score=3 + (i % 3),
                sentiment="POSITIVE" if i % 2 == 0 else "NEGATIVE",
            )
        result = aggregate_month(2026, 2)
        assert len(list(result["news"])) == 5  # display cap
        assert result["news_total"] == 8       # real count

    def test_news_sentiment_breakdown_counts_full_set(self, db):
        from newswatch.models import NewsArticle
        from datetime import date as _date
        for sentiment, count in [("POSITIVE", 4), ("NEGATIVE", 2), ("NEUTRAL", 6)]:
            for i in range(count):
                NewsArticle.objects.create(
                    url=f"https://example.com/{sentiment}-{i}",
                    title=f"{sentiment} {i}",
                    published_date=_date(2026, 2, 10),
                    status=NewsArticle.ANALYSED,
                    review_status=NewsArticle.APPROVED,
                    sentiment=sentiment,
                    relevance_score=3,
                )
        result = aggregate_month(2026, 2)
        assert result["news_sentiment_breakdown"] == {
            "positive": 4, "negative": 2, "neutral": 6,
        }

    def test_parliament_was_in_session_true_when_sittings_exist(self, sitting_feb):
        result = aggregate_month(2026, 2)
        assert result["parliament_was_in_session"] is True
        assert result["parliament_sitting_count"] >= 1

    def test_parliament_was_in_session_false_when_no_sittings(self, db):
        # April 2026 — recess, no sittings created in fixtures
        result = aggregate_month(2026, 4)
        assert result["parliament_was_in_session"] is False
        assert result["parliament_sitting_count"] == 0

    def test_parliament_was_in_session_false_when_only_failed_sittings(self, db):
        # Scraper probes every calendar date; non-sitting days (recess,
        # weekend, public holiday) land as FAILED rows. The recess
        # detection must ignore those — only COMPLETED rows count as
        # evidence Parliament actually sat.
        HansardSitting.objects.create(
            sitting_date=date(2026, 4, 5),
            pdf_url="https://example.com/apr-5.pdf",
            pdf_filename="apr-5.pdf",
            status=HansardSitting.Status.FAILED,
        )
        HansardSitting.objects.create(
            sitting_date=date(2026, 4, 12),
            pdf_url="https://example.com/apr-12.pdf",
            pdf_filename="apr-12.pdf",
            status=HansardSitting.Status.FAILED,
        )
        result = aggregate_month(2026, 4)
        assert result["parliament_was_in_session"] is False
        assert result["parliament_sitting_count"] == 0

    def test_schools_mentioned_unions_news_and_hansard(self, db):
        """Schools mentioned in news (via JSON moe_code) AND Hansard
        (via MentionedSchool FK) should both appear, deduplicated."""
        from newswatch.models import NewsArticle
        from schools.models import School, Constituency, DUN
        from datetime import date as _date
        c = Constituency.objects.create(code="P999", name="Test", state="TestState")
        d = DUN.objects.create(code="N999", name="TestDUN", constituency=c, state="TestState")
        s1 = School.objects.create(
            moe_code="ZZZ0001", name="SJK(T) Alpha", short_name="Alpha",
            state="TestState", ppd="TestPPD", constituency=c, dun=d,
        )
        s2 = School.objects.create(
            moe_code="ZZZ0002", name="SJK(T) Beta", short_name="Beta",
            state="TestState", ppd="TestPPD", constituency=c, dun=d,
        )
        NewsArticle.objects.create(
            url="https://example.com/x",
            title="X",
            published_date=_date(2026, 2, 5),
            status=NewsArticle.ANALYSED,
            review_status=NewsArticle.APPROVED,
            mentioned_schools=[
                {"name": "SJK(T) Alpha", "moe_code": "ZZZ0001"},
                {"name": "SJK(T) Beta", "moe_code": "ZZZ0002"},
            ],
        )
        result = aggregate_month(2026, 2)
        moe_codes = {s.moe_code for s in result["schools_mentioned"]}
        assert "ZZZ0001" in moe_codes
        assert "ZZZ0002" in moe_codes
        assert result["schools_mentioned_total"] == len(result["schools_mentioned"])
