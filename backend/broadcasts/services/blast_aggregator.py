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

COUNT-vs-SAMPLE POLICY (Sprint 23):
  Headline numbers ("46 news articles this month") MUST be real DB
  counts, not the length of a display-capped sample. The aggregator
  returns BOTH:
    - `news_total`, `parliament_total`, `schools_mentioned_total`,
      `news_sentiment_breakdown`, `parliament_sitting_count`
      — deterministic counts for headline stats and prompt context.
    - `news`, `parliament`, `briefs`, `meeting_reports`, `scorecards`
      — display-capped samples for narrative rendering.

  Sprint 18's monthly-analyst LLM was previously asked to compute
  `by_the_numbers` from the text-formatted top-5 sample, leading to
  invented schools_affected counts and a "5 News Articles" stat in
  the April 2026 digest when 46 were actually approved. Sprint 23
  removed `by_the_numbers` from the LLM schema; it is now composed
  in Python from the deterministic counts here.

STAT SEMANTICS — locked Sprint 24 task #3:
  Every headline number in the v2 template has a single, locked
  definition. Future contributors who change ANY of these MUST update
  both the template caption AND this docstring. Subscribers screenshot
  the digest; the captions are a contract.

  parliament_total
    Number of HansardMention rows whose `sitting.sitting_date` falls
    within the target month AND review_status != REJECTED AND mp_name
    is non-empty. One row = one mention by one MP in one sitting; a
    single MP raising SJK(T) three times in one debate counts as one.
    Recess months → zero (no sittings = no mentions).

  news_total
    Number of NewsArticle rows whose `published_date` falls within
    the target month AND status=ANALYSED AND review_status=APPROVED.
    The "approved" gate is auto-applied at relevance_score>=3 by the
    news_analyser pipeline (Sprint 24 #1a tightened the relevance
    prompt + added a domain blocklist). This is the raw article
    count, NOT the topic-cluster count produced by
    services.topic_clusterer — clusters group articles, they don't
    replace the headline.

  schools_mentioned_total
    Number of distinct School rows mentioned in either news OR
    Hansard during the month. Schools mentioned only by name (no
    matched moe_code) are NOT counted — we count rows we could
    confidently link, not LLM-reported names. The same school
    mentioned 5 times in news + 2 times in Hansard counts as one.

  news_sentiment_breakdown.positive / .negative / .neutral
    Counts taken from news_all filtered by NewsArticle.sentiment.
    Headline "positive stories" = positive count. MIXED-sentiment
    articles are NOT in any of the three buckets; if MIXED becomes
    common, surface a separate "mixed" key here.

  schools_by_state (Sprint 24 #3)
    dict[str, list[School]] mapping state name (e.g. "Melaka",
    "Pulau Pinang") to the schools_mentioned subset in that state.
    Insertion order is by count descending, then alphabetical — so
    the v2 template can iterate in display order without re-sorting.
    Schools with empty/null state land in the catch-all key
    "Other" so the row count always matches schools_mentioned_total.

  parliament_was_in_session
    True iff at least one HansardSitting row with status=COMPLETED
    exists in the month. FAILED rows (probe-day with no PDF) don't
    count — they are evidence of recess, not sitting. This boolean
    drives every RECESS clause in monthly_analyst.ANALYST_PROMPT.

  parliament_sitting_count
    Count of HansardSitting rows with status=COMPLETED in the month.
    Caption text "in N sittings" beside parliament_total reads this.
"""

from datetime import date

from django.db.models import Q

from hansard.models import HansardMention, HansardSitting, MentionedSchool
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

        DISPLAY-CAPPED SAMPLES (for narrative rendering):
        - parliament: up to 5 HansardMentions (excluding REJECTED), by
          significance desc.
        - news: up to 5 approved NewsArticles, by relevance_score desc.
          Sprint 23: also returned in full as `news_all` for visibility.
        - briefs: SittingBriefs whose sitting_date falls in the month
          (or backfill window). Up to 5, newest first.
        - meeting_reports: ParliamentaryMeetings whose period overlaps
          the month (or whose published_at falls in the backfill
          window). Up to 3, newest first.
        - scorecards: up to 3 MPScorecards filtered by activity in the
          month. If none, falls back to top-3 lifetime so the section
          isn't blank in quiet months — flagged via 'lifetime' key.

        DETERMINISTIC COUNTS (Sprint 23, for headline stats):
        - parliament_total (int): count of all non-REJECTED HansardMentions
          in the month.
        - news_total (int): count of all APPROVED NewsArticles in the month.
        - news_sentiment_breakdown (dict): {positive, negative, neutral}
          counts from the full APPROVED-news set.
        - schools_mentioned (list[School]): unique School objects mentioned
          in either news OR Hansard in the month, sorted by name.
        - schools_mentioned_total (int): len(schools_mentioned).
        - schools_by_state (dict[str, list[School]]): same schools grouped
          by School.state, ordered by count desc then state name asc.
          Schools with missing state land in "Other".
        - news_all (queryset): full APPROVED news for the month, ordered
          by relevance_score desc — for the visibility section in the
          email.
        - parliament_was_in_session (bool): True if any HansardSitting
          exists in the month — drives the recess copy in the template.
        - parliament_sitting_count (int): number of sittings in the month.
    """
    month_start, month_end = _month_bounds(year, month)

    # HansardMention — match public-site policy (exclude REJECTED, not
    # require APPROVED). The default value is PENDING; the prior
    # require-APPROVED filter silently dropped any mention nobody had
    # explicitly triaged.
    parliament_qs = (
        HansardMention.objects.filter(
            sitting__sitting_date__year=year,
            sitting__sitting_date__month=month,
        )
        .exclude(review_status="REJECTED")
        .exclude(mp_name="")
        .select_related("sitting")
    )
    parliament_total = parliament_qs.count()
    parliament = parliament_qs.order_by("-significance")[:5]

    news_all = (
        NewsArticle.objects.filter(
            published_date__year=year,
            published_date__month=month,
            status=NewsArticle.ANALYSED,
            review_status=NewsArticle.APPROVED,
        )
        .order_by("-relevance_score")
    )
    news_total = news_all.count()
    news = news_all[:5]
    news_sentiment_breakdown = {
        "positive": news_all.filter(sentiment="POSITIVE").count(),
        "negative": news_all.filter(sentiment="NEGATIVE").count(),
        "neutral": news_all.filter(sentiment="NEUTRAL").count(),
    }

    # Schools mentioned this month — union across news + Hansard. Used
    # for the "Schools in the news" visibility section AND the headline
    # "schools_affected" stat. Pre-Sprint-23 the headline number was
    # LLM-imputed from a 5-article sample (typically 20-30, often
    # fabricated); now it's a real DB count.
    #
    # NewsArticle.mentioned_schools is a JSONField shaped as
    # [{"name": "SJK(T) Foo", "moe_code": "ABD1234"}, ...] — produced
    # by the AI pipeline. We look up by moe_code (most reliable);
    # entries without a moe_code are skipped (rare, name-only matches
    # would need fuzzy logic).
    moe_codes_in_news = set()
    for article in news_all:
        for entry in (article.mentioned_schools or []):
            if isinstance(entry, dict) and entry.get("moe_code"):
                moe_codes_in_news.add(entry["moe_code"])
    school_ids_from_hansard = set(
        MentionedSchool.objects.filter(
            mention__sitting__sitting_date__year=year,
            mention__sitting__sitting_date__month=month,
        )
        .exclude(mention__review_status="REJECTED")
        .values_list("school_id", flat=True)
    )
    from schools.models import School  # local to avoid circular import on app load
    schools_mentioned = list(
        School.objects.filter(
            Q(pk__in=school_ids_from_hansard) | Q(moe_code__in=moe_codes_in_news)
        ).order_by("name")
    )
    schools_mentioned_total = len(schools_mentioned)

    # Sprint 24 task #3: schools_by_state — group the mentioned schools
    # by state for the v2 template's per-state section. Sorted by count
    # descending then state name ascending so the template can iterate
    # without re-sorting. Schools with missing/empty state land in
    # "Other" so the row count matches schools_mentioned_total.
    state_buckets: dict[str, list] = {}
    for school in schools_mentioned:
        key = (school.state or "").strip() or "Other"
        state_buckets.setdefault(key, []).append(school)
    schools_by_state = dict(
        sorted(
            state_buckets.items(),
            key=lambda kv: (-len(kv[1]), kv[0]),
        )
    )

    # Recess detection (Sprint 23) — was Parliament even sitting?
    # The scraper creates a HansardSitting row per CALENDAR DATE it
    # probes; if no PDF exists for that date (recess, weekend, public
    # holiday) the row is marked FAILED. So "Parliament sat" must
    # filter for COMPLETED rows — FAILED rows are evidence of the
    # opposite.
    sitting_count = HansardSitting.objects.filter(
        sitting_date__year=year,
        sitting_date__month=month,
        status=HansardSitting.Status.COMPLETED,
    ).count()
    parliament_was_in_session = sitting_count > 0

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
        # Display-capped samples (existing keys, unchanged shape)
        "parliament": parliament,
        "news": news,
        "briefs": briefs,
        "meeting_reports": meeting_reports,
        "scorecards": scorecards,
        "scorecards_are_lifetime_fallback": used_lifetime_fallback,
        # Sprint 23: deterministic counts + full lists for visibility
        "parliament_total": parliament_total,
        "news_total": news_total,
        "news_all": news_all,
        "news_sentiment_breakdown": news_sentiment_breakdown,
        "schools_mentioned": schools_mentioned,
        "schools_mentioned_total": schools_mentioned_total,
        "schools_by_state": schools_by_state,
        "parliament_was_in_session": parliament_was_in_session,
        "parliament_sitting_count": sitting_count,
    }
