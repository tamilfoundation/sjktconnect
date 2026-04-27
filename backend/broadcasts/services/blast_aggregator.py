"""
Aggregator service for the Monthly Intelligence Blast.

Queries the content that should appear in the digest for a given month.
Optionally widens the lookback window via `backfill_since` so a one-time
"catching-up" digest can pick up content that was missed by prior runs
(e.g. a meeting report published just before the month boundary).

DATE-SEMANTICS POLICY (Sprint 18, see docs/lessons.md):
  Each source uses the date field that matches user expectation of
  "what happened this month" — not "what was approved by the cron's
  runtime". Approval-status filters mirror the public site so the
  digest can never report 0 of something the public site shows N of.

  | Source                | Filter date          | Approval gate           |
  |-----------------------|----------------------|-------------------------|
  | HansardMention        | sitting.sitting_date | exclude(REJECTED)       |
  | NewsArticle           | published_date       | review_status=APPROVED  |
  | SittingBrief          | sitting.sitting_date | is_published=True       |
  | ParliamentaryMeeting  | start/end overlap    | is_published=True       |
  | MPScorecard           | last_mention_date    | (no extra gate)         |

  HansardMention default review_status is "PENDING" — Sprint 18 found
  that filtering on APPROVED dropped 3 mentions from the 1 Apr 2026
  digest because nobody had explicitly approved them, even though they
  were live on the public site. exclude(REJECTED) matches the public
  policy.

  ParliamentaryMeeting "overlap" filter: include any meeting where the
  meeting period (start_date..end_date) intersects the target month.
  This catches a meeting that started in Jan and ran into early March,
  for both Jan, Feb, and March digests — which matches user mental
  model (the meeting is "active" in those months).
"""

from datetime import date

from hansard.models import HansardMention
from newswatch.models import NewsArticle
from parliament.models import MPScorecard, ParliamentaryMeeting, SittingBrief


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    """Return (first_day, last_day) inclusive for a calendar month."""
    import calendar
    first = date(year, month, 1)
    last = date(year, month, calendar.monthrange(year, month)[1])
    return first, last


def aggregate_month(
    year: int,
    month: int,
    backfill_since: date | None = None,
) -> dict:
    """Aggregate top content for a given month for the monthly digest.

    Args:
        year, month: Target month.
        backfill_since: Optional. If set, sitting briefs and meeting
            reports also include any item with sitting_date >=
            backfill_since (briefs) or published_at >= backfill_since
            (meeting reports) that isn't already in the month-overlap
            set. Used once to fill a gap when a prior digest missed
            content. Has no effect on mentions, news, or scorecards.

    Returns:
        dict with keys:
        - parliament: up to 5 HansardMentions (excluding REJECTED), by
          significance desc.
        - news: up to 5 approved NewsArticles, by relevance_score desc.
        - briefs: SittingBriefs whose sitting_date falls in the month
          (or backfill window). Up to 5, newest first.
        - meeting_reports: ParliamentaryMeetings whose period overlaps
          the month (or whose published_at falls in the backfill
          window). Up to 3, newest first.
        - scorecards: up to 3 MPScorecards filtered by activity in the
          month. If none, falls back to top-3 lifetime so the section
          isn't blank in quiet months — flagged via 'lifetime' key.
    """
    month_start, month_end = _month_bounds(year, month)

    # HansardMention — match public-site policy (exclude REJECTED, not
    # require APPROVED). The default value is PENDING; the prior
    # require-APPROVED filter silently dropped any mention nobody had
    # explicitly triaged.
    parliament = (
        HansardMention.objects.filter(
            sitting__sitting_date__year=year,
            sitting__sitting_date__month=month,
        )
        .exclude(review_status="REJECTED")
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

    # SittingBriefs whose sitting_date falls in the month (or backfill
    # window). NOTE on is_published: the public parliament_watch
    # endpoints (parliament/api/views.py) DO NOT filter by
    # is_published — they show every brief regardless. Sprint 18
    # discovered the original is_published=True filter here was
    # stricter than the public site, which (per the lesson written
    # alongside this code) is exactly the bug we're trying to avoid:
    # the aggregator must mirror public visibility, not its own
    # narrower policy. So no is_published filter here.
    brief_qs = SittingBrief.objects.select_related("sitting")
    if backfill_since:
        briefs_in_month = brief_qs.filter(
            sitting__sitting_date__gte=month_start,
            sitting__sitting_date__lte=month_end,
        )
        briefs_backfill = brief_qs.filter(
            sitting__sitting_date__gte=backfill_since,
            sitting__sitting_date__lt=month_start,
        )
        briefs = (briefs_in_month | briefs_backfill).order_by("-sitting__sitting_date")[:5]
    else:
        briefs = brief_qs.filter(
            sitting__sitting_date__gte=month_start,
            sitting__sitting_date__lte=month_end,
        ).order_by("-sitting__sitting_date")[:5]

    # ParliamentaryMeeting reports — meeting overlaps the month, OR
    # (when backfilling) the report was published in the backfill
    # window. Same is_published note as briefs above: the public
    # /parliament-watch/ endpoints don't filter on it, so we don't
    # either.
    meeting_qs = ParliamentaryMeeting.objects.all()
    overlap_meetings = meeting_qs.filter(
        start_date__lte=month_end,
        end_date__gte=month_start,
    )
    if backfill_since:
        # Use end_date (not published_at) because most rows have
        # published_at=None even when the report PDF exists. The
        # natural user intent for "backfill meetings I missed since X"
        # is "any meeting that ended between X and the start of the
        # target month and isn't already in the overlap set."
        backfill_meetings = meeting_qs.filter(
            end_date__gte=backfill_since,
            end_date__lt=month_start,
        )
        meeting_reports = (overlap_meetings | backfill_meetings).distinct().order_by("-end_date")[:3]
    else:
        meeting_reports = overlap_meetings.order_by("-end_date")[:3]

    # MPScorecard — Sprint 18: prefer scorecards with activity in the
    # month (so we don't keep showing the same top-3 forever-active
    # MPs). Fall back to lifetime top-3 only when no MP was active
    # this month, so the section isn't blank.
    scorecards = (
        MPScorecard.objects.filter(last_mention_date__gte=month_start)
        .filter(last_mention_date__lte=month_end)
        .select_related("constituency")
        .order_by("-total_mentions")[:3]
    )
    used_lifetime_fallback = False
    if not scorecards.exists():
        scorecards = (
            MPScorecard.objects.select_related("constituency")
            .order_by("-total_mentions")[:3]
        )
        used_lifetime_fallback = True

    return {
        "parliament": parliament,
        "news": news,
        "briefs": briefs,
        "meeting_reports": meeting_reports,
        "scorecards": scorecards,
        "scorecards_are_lifetime_fallback": used_lifetime_fallback,
    }
