# Monthly Intelligence Blast — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a management command that auto-drafts a monthly digest email aggregating Parliament Watch mentions, News Watch articles, and MP Scorecard highlights into an existing Broadcast for admin review and sending.

**Architecture:** New `blast_aggregator.py` service queries approved HansardMentions, approved NewsArticles, and top MPScorecards for a given month. A new `compose_monthly_blast` management command renders these into an HTML email template and creates a DRAFT Broadcast. Admin reviews via existing broadcast preview UI and sends via existing Brevo infrastructure.

**Tech Stack:** Django 5.1, pytest, existing Broadcast + Subscriber models

---

### Task 1: blast_aggregator service — tests

**Files:**
- Create: `backend/broadcasts/tests/test_blast_aggregator.py`

**Step 1: Write the test file**

```python
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
        """No data for the month returns empty lists."""
        result = aggregate_month(2026, 2)
        assert list(result["parliament"]) == []
        assert list(result["news"]) == []
        assert list(result["scorecards"]) == []

    def test_parliament_filters_by_month_and_approved(self, sitting_feb, sitting_jan):
        """Only APPROVED mentions from the target month are included."""
        approved_feb = _make_mention(sitting_feb, 4, "APPROVED")
        _make_mention(sitting_feb, 3, "REJECTED")  # rejected — excluded
        _make_mention(sitting_feb, 2, "PENDING")   # pending — excluded
        _make_mention(sitting_jan, 5, "APPROVED")  # wrong month — excluded

        result = aggregate_month(2026, 2)
        mentions = list(result["parliament"])
        assert len(mentions) == 1
        assert mentions[0].pk == approved_feb.pk

    def test_parliament_ordered_by_significance_desc(self, sitting_feb):
        """Mentions are ordered by significance descending (highest first)."""
        low = _make_mention(sitting_feb, 2, "APPROVED", "MP Low")
        high = _make_mention(sitting_feb, 5, "APPROVED", "MP High")
        mid = _make_mention(sitting_feb, 3, "APPROVED", "MP Mid")

        result = aggregate_month(2026, 2)
        pks = [m.pk for m in result["parliament"]]
        assert pks == [high.pk, mid.pk, low.pk]

    def test_parliament_limited_to_5(self, sitting_feb):
        """At most 5 parliament mentions are returned."""
        for i in range(7):
            _make_mention(sitting_feb, 5 - (i % 5), "APPROVED", f"MP {i}")

        result = aggregate_month(2026, 2)
        assert len(list(result["parliament"])) == 5

    def test_news_filters_by_month_and_approved(self, db):
        """Only APPROVED, ANALYSED articles from the target month."""
        feb_date = timezone.make_aware(datetime(2026, 2, 15))
        jan_date = timezone.make_aware(datetime(2026, 1, 15))

        approved = _make_article("Good", 4, "APPROVED", feb_date)
        _make_article("Bad", 3, "REJECTED", feb_date)   # rejected
        _make_article("Old", 5, "APPROVED", jan_date)    # wrong month

        result = aggregate_month(2026, 2)
        articles = list(result["news"])
        assert len(articles) == 1
        assert articles[0].pk == approved.pk

    def test_news_ordered_by_relevance_desc(self, db):
        """Articles ordered by relevance_score descending."""
        feb = timezone.make_aware(datetime(2026, 2, 10))
        low = _make_article("Low", 2, "APPROVED", feb)
        high = _make_article("High", 5, "APPROVED", feb)

        result = aggregate_month(2026, 2)
        pks = [a.pk for a in result["news"]]
        assert pks == [high.pk, low.pk]

    def test_news_limited_to_5(self, db):
        """At most 5 news articles are returned."""
        feb = timezone.make_aware(datetime(2026, 2, 10))
        for i in range(7):
            _make_article(f"Article {i}", 3, "APPROVED", feb)

        result = aggregate_month(2026, 2)
        assert len(list(result["news"])) == 5

    def test_scorecards_ordered_by_total_mentions(self, constituency):
        """Scorecards ordered by total_mentions descending."""
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
        """At most 3 scorecards are returned."""
        for i in range(5):
            MPScorecard.objects.create(
                mp_name=f"MP {i}", constituency=constituency, total_mentions=i
            )

        result = aggregate_month(2026, 2)
        assert len(list(result["scorecards"])) == 3

    def test_returns_dict_with_three_keys(self):
        """Result has exactly parliament, news, scorecards keys."""
        result = aggregate_month(2026, 2)
        assert set(result.keys()) == {"parliament", "news", "scorecards"}
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest broadcasts/tests/test_blast_aggregator.py -v`
Expected: ImportError — `blast_aggregator` does not exist yet

**Step 3: Commit test file**

```bash
git add backend/broadcasts/tests/test_blast_aggregator.py
git commit -m "test: add blast_aggregator service tests (red phase)"
```

---

### Task 2: blast_aggregator service — implementation

**Files:**
- Create: `backend/broadcasts/services/blast_aggregator.py`

**Step 1: Implement the service**

```python
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
```

**Step 2: Run tests to verify they pass**

Run: `cd backend && python -m pytest broadcasts/tests/test_blast_aggregator.py -v`
Expected: All 11 tests PASS

**Step 3: Commit**

```bash
git add backend/broadcasts/services/blast_aggregator.py
git commit -m "feat: add blast_aggregator service for monthly digest"
```

---

### Task 3: Email template

**Files:**
- Create: `backend/templates/broadcasts/monthly_blast.html`

**Step 1: Create the email template**

This is a Django template that renders the aggregated data into HTML email content. It will be passed to `_wrap_broadcast_html()` by the management command, so it only needs to produce the inner content (no DOCTYPE, no `<html>`/`<body>` wrapper).

```html
<h1 style="color: #1a1a2e; font-size: 24px; margin-bottom: 5px;">Monthly Intelligence Blast</h1>
<p style="color: #666; font-size: 14px; margin-top: 0;">{{ month_label }}</p>
<hr style="border: none; border-top: 2px solid #e0e0e0; margin: 20px 0;">

{% if parliament %}
<h2 style="color: #2c3e50; font-size: 18px;">Parliament Watch</h2>
<p style="color: #888; font-size: 13px;">Top mentions of Tamil schools in Hansard this month</p>
{% for mention in parliament %}
<div style="background: #f8f9fa; border-left: 3px solid #3498db; padding: 12px 15px; margin-bottom: 12px; border-radius: 0 4px 4px 0;">
    <p style="margin: 0 0 4px 0; font-weight: bold; color: #2c3e50;">
        {{ mention.mp_name }}
        {% if mention.mp_constituency %}<span style="font-weight: normal; color: #888;"> &mdash; {{ mention.mp_constituency }}</span>{% endif %}
    </p>
    <p style="margin: 0 0 4px 0; font-size: 13px; color: #666;">
        {{ mention.sitting.sitting_date|date:"j M Y" }}
        &middot; Significance: {{ mention.significance }}/5
        {% if mention.mention_type %}&middot; {{ mention.mention_type }}{% endif %}
    </p>
    {% if mention.ai_summary %}<p style="margin: 0; color: #333;">{{ mention.ai_summary }}</p>{% endif %}
</div>
{% endfor %}
<hr style="border: none; border-top: 1px solid #e0e0e0; margin: 20px 0;">
{% endif %}

{% if news %}
<h2 style="color: #2c3e50; font-size: 18px;">News Watch</h2>
<p style="color: #888; font-size: 13px;">Top news articles about Tamil schools this month</p>
{% for article in news %}
<div style="background: #f8f9fa; border-left: 3px solid #27ae60; padding: 12px 15px; margin-bottom: 12px; border-radius: 0 4px 4px 0;">
    <p style="margin: 0 0 4px 0; font-weight: bold; color: #2c3e50;">
        <a href="{{ article.url }}" style="color: #2c3e50; text-decoration: none;">{{ article.title|truncatechars:80 }}</a>
    </p>
    <p style="margin: 0 0 4px 0; font-size: 13px; color: #666;">
        {{ article.source_name|default:"Unknown" }}
        {% if article.published_date %}&middot; {{ article.published_date|date:"j M Y" }}{% endif %}
        &middot; Relevance: {{ article.relevance_score }}/5
        &middot; <span style="text-transform: capitalize;">{{ article.sentiment|lower }}</span>
    </p>
    {% if article.ai_summary %}<p style="margin: 0; color: #333;">{{ article.ai_summary|truncatechars:200 }}</p>{% endif %}
</div>
{% endfor %}
<hr style="border: none; border-top: 1px solid #e0e0e0; margin: 20px 0;">
{% endif %}

{% if scorecards %}
<h2 style="color: #2c3e50; font-size: 18px;">MP Scorecard Highlights</h2>
<p style="color: #888; font-size: 13px;">Most active MPs on Tamil school issues</p>
<table style="width: 100%; border-collapse: collapse; font-size: 14px;">
    <tr style="background: #f1f1f1;">
        <th style="text-align: left; padding: 8px;">MP</th>
        <th style="text-align: left; padding: 8px;">Constituency</th>
        <th style="text-align: center; padding: 8px;">Mentions</th>
        <th style="text-align: center; padding: 8px;">Substantive</th>
    </tr>
    {% for sc in scorecards %}
    <tr style="border-bottom: 1px solid #e0e0e0;">
        <td style="padding: 8px; font-weight: bold;">{{ sc.mp_name }}</td>
        <td style="padding: 8px;">{{ sc.constituency|default:"Unknown" }}</td>
        <td style="padding: 8px; text-align: center;">{{ sc.total_mentions }}</td>
        <td style="padding: 8px; text-align: center;">{{ sc.substantive_mentions }}</td>
    </tr>
    {% endfor %}
</table>
{% endif %}

{% if not parliament and not news and not scorecards %}
<p style="color: #888; text-align: center; padding: 30px 0;">No intelligence data available for {{ month_label }}.</p>
{% endif %}
```

**Step 2: Commit**

```bash
git add backend/templates/broadcasts/monthly_blast.html
git commit -m "feat: add monthly blast email template"
```

---

### Task 4: compose_monthly_blast command — tests

**Files:**
- Create: `backend/broadcasts/tests/test_compose_command.py`

**Step 1: Write the test file**

```python
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
        """Command creates a DRAFT broadcast with rendered content."""
        out = StringIO()
        call_command("compose_monthly_blast", month="2026-02", stdout=out)

        assert Broadcast.objects.count() == 1
        broadcast = Broadcast.objects.first()
        assert broadcast.status == Broadcast.Status.DRAFT
        assert "February 2026" in broadcast.subject

    def test_broadcast_contains_parliament_content(self, mention):
        """Broadcast HTML includes parliament mention data."""
        call_command("compose_monthly_blast", month="2026-02")
        broadcast = Broadcast.objects.first()
        assert "YB Test" in broadcast.html_content
        assert "Parliament Watch" in broadcast.html_content

    def test_broadcast_contains_news_content(self, article):
        """Broadcast HTML includes news article data."""
        call_command("compose_monthly_blast", month="2026-02")
        broadcast = Broadcast.objects.first()
        assert "Tamil School News" in broadcast.html_content
        assert "News Watch" in broadcast.html_content

    def test_broadcast_contains_scorecard_content(self, scorecard):
        """Broadcast HTML includes scorecard data."""
        call_command("compose_monthly_blast", month="2026-02")
        broadcast = Broadcast.objects.first()
        assert "YB Top" in broadcast.html_content
        assert "Scorecard" in broadcast.html_content

    def test_audience_filter_set_to_monthly_blast(self, mention):
        """Broadcast audience_filter targets MONTHLY_BLAST category."""
        call_command("compose_monthly_blast", month="2026-02")
        broadcast = Broadcast.objects.first()
        assert broadcast.audience_filter == {"category": "MONTHLY_BLAST"}

    def test_dry_run_does_not_create_broadcast(self, mention):
        """--dry-run prints summary without creating a broadcast."""
        out = StringIO()
        call_command("compose_monthly_blast", month="2026-02", dry_run=True, stdout=out)

        assert Broadcast.objects.count() == 0
        output = out.getvalue()
        assert "DRY RUN" in output

    def test_dry_run_shows_counts(self, mention, article, scorecard):
        """--dry-run output shows item counts."""
        out = StringIO()
        call_command("compose_monthly_blast", month="2026-02", dry_run=True, stdout=out)
        output = out.getvalue()
        assert "1 parliament" in output
        assert "1 news" in output
        assert "1 scorecard" in output

    def test_defaults_to_previous_month(self, db):
        """Without --month, defaults to previous month."""
        out = StringIO()
        call_command("compose_monthly_blast", stdout=out)
        # Should not raise — creates a broadcast for previous month
        assert Broadcast.objects.count() == 1

    def test_invalid_month_format_raises_error(self, db):
        """Invalid --month format raises CommandError."""
        with pytest.raises(CommandError, match="Invalid month format"):
            call_command("compose_monthly_blast", month="Feb-2026")

    def test_empty_month_still_creates_broadcast(self, db):
        """A month with no data still creates a broadcast with empty-state message."""
        call_command("compose_monthly_blast", month="2026-02")
        broadcast = Broadcast.objects.first()
        assert broadcast is not None
        assert "No intelligence data" in broadcast.html_content

    def test_subject_format(self, mention):
        """Subject follows expected format."""
        call_command("compose_monthly_blast", month="2026-02")
        broadcast = Broadcast.objects.first()
        assert broadcast.subject == "Monthly Intelligence Blast — February 2026"

    def test_text_content_generated(self, mention):
        """Broadcast includes plain-text fallback."""
        call_command("compose_monthly_blast", month="2026-02")
        broadcast = Broadcast.objects.first()
        assert broadcast.text_content != ""
        assert "Parliament Watch" in broadcast.text_content

    def test_prints_broadcast_id(self, mention):
        """Command output includes the created broadcast ID."""
        out = StringIO()
        call_command("compose_monthly_blast", month="2026-02", stdout=out)
        broadcast = Broadcast.objects.first()
        assert str(broadcast.pk) in out.getvalue()
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest broadcasts/tests/test_compose_command.py -v`
Expected: ImportError — command does not exist yet

**Step 3: Commit test file**

```bash
git add backend/broadcasts/tests/test_compose_command.py
git commit -m "test: add compose_monthly_blast command tests (red phase)"
```

---

### Task 5: compose_monthly_blast command — implementation

**Files:**
- Create: `backend/broadcasts/management/commands/compose_monthly_blast.py`
- Ensure: `backend/broadcasts/management/__init__.py` and `backend/broadcasts/management/commands/__init__.py` exist

**Step 1: Check management directory exists**

Run: `ls backend/broadcasts/management/commands/`
If missing, create `__init__.py` files.

**Step 2: Implement the command**

```python
"""
Management command to compose a Monthly Intelligence Blast.

Aggregates the top approved Parliament Watch mentions, News Watch articles,
and MP Scorecards for a given month, renders them into an HTML email, and
creates a DRAFT Broadcast for admin review.

Usage:
    python manage.py compose_monthly_blast                # Previous month
    python manage.py compose_monthly_blast --month 2026-02
    python manage.py compose_monthly_blast --month 2026-02 --dry-run
"""

import calendar
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from broadcasts.models import Broadcast
from broadcasts.services.blast_aggregator import aggregate_month


class Command(BaseCommand):
    help = "Compose a Monthly Intelligence Blast as a DRAFT broadcast."

    def add_arguments(self, parser):
        parser.add_argument(
            "--month",
            type=str,
            default="",
            help="Target month in YYYY-MM format (default: previous month)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be included without creating a broadcast",
        )

    def handle(self, *args, **options):
        year, month = self._parse_month(options["month"])
        month_label = f"{calendar.month_name[month]} {year}"
        dry_run = options["dry_run"]

        data = aggregate_month(year, month)

        parliament_count = len(list(data["parliament"]))
        news_count = len(list(data["news"]))
        scorecard_count = len(list(data["scorecards"]))

        if dry_run:
            self.stdout.write(f"DRY RUN — {month_label}")
            self.stdout.write(
                f"  {parliament_count} parliament, "
                f"{news_count} news, "
                f"{scorecard_count} scorecard items"
            )
            return

        # Re-query because querysets may be consumed by len(list(...))
        data = aggregate_month(year, month)

        html_content = render_to_string(
            "broadcasts/monthly_blast.html",
            {
                "month_label": month_label,
                "parliament": data["parliament"],
                "news": data["news"],
                "scorecards": data["scorecards"],
            },
        )

        text_content = strip_tags(html_content)

        broadcast = Broadcast.objects.create(
            subject=f"Monthly Intelligence Blast — {month_label}",
            html_content=html_content,
            text_content=text_content,
            audience_filter={"category": "MONTHLY_BLAST"},
            status=Broadcast.Status.DRAFT,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Draft broadcast created (ID: {broadcast.pk}) with "
                f"{parliament_count} parliament, {news_count} news, "
                f"{scorecard_count} scorecard items"
            )
        )

    def _parse_month(self, month_str: str) -> tuple[int, int]:
        """Parse YYYY-MM string or default to previous month."""
        if not month_str:
            today = date.today()
            if today.month == 1:
                return today.year - 1, 12
            return today.year, today.month - 1

        try:
            parts = month_str.split("-")
            return int(parts[0]), int(parts[1])
        except (ValueError, IndexError):
            raise CommandError(
                f"Invalid month format: '{month_str}'. Use YYYY-MM (e.g. 2026-02)."
            )
```

**Step 3: Run tests to verify they pass**

Run: `cd backend && python -m pytest broadcasts/tests/test_compose_command.py -v`
Expected: All 13 tests PASS

**Step 4: Commit**

```bash
git add backend/broadcasts/management/ backend/templates/broadcasts/monthly_blast.html
git commit -m "feat: add compose_monthly_blast management command"
```

---

### Task 6: Run full test suite

**Step 1: Run all backend tests**

Run: `cd backend && python -m pytest --tb=short -q`
Expected: All existing + new tests pass. Should be ~782 tests (758 existing + 24 new).

**Step 2: Fix any failures**

If tests fail, investigate and fix. Common issues:
- Import paths — verify `broadcasts.services.blast_aggregator` is importable
- Template path — verify `broadcasts/monthly_blast.html` is found by Django template loader
- Fixture conflicts — ensure test fixtures don't clash with existing ones

**Step 3: Commit if any fixes were needed**

```bash
git add -A
git commit -m "fix: resolve test issues from monthly blast integration"
```

---

### Task 7: Documentation updates

**Files:**
- Modify: `CHANGELOG.md` — add Sprint 2.7 entry at top
- Modify: `CLAUDE.md` — update sprint info, test count, command list

**Step 1: Update CHANGELOG.md**

Add at the top of the file, under the heading:

```markdown
## Sprint 2.7 — Monthly Intelligence Blast (2 Mar 2026)

### Added
- `blast_aggregator.py` service: queries top 5 approved Hansard mentions, top 5 approved news articles, top 3 MP scorecards for a given month
- `compose_monthly_blast` management command with `--month YYYY-MM` and `--dry-run` flags
- `monthly_blast.html` email template with three sections (Parliament Watch, News Watch, MP Scorecard Highlights)
- 24 new backend tests (blast aggregator service + management command)

### Technical
- No new models — reuses existing Broadcast, HansardMention, NewsArticle, MPScorecard
- Audience filter set to MONTHLY_BLAST category for subscriber targeting
- Plain-text fallback auto-generated via strip_tags
- Admin reviews draft via existing broadcast preview UI, sends via existing Brevo infrastructure
```

**Step 2: Update CLAUDE.md**

- Update last sprint to 2.7
- Update test count
- Add `compose_monthly_blast` to command list
- Update sprint history

**Step 3: Commit**

```bash
git add CHANGELOG.md CLAUDE.md
git commit -m "docs: update CHANGELOG and CLAUDE.md for Sprint 2.7"
```

---

## Summary

| Task | What | Tests | Files |
|------|------|-------|-------|
| 1 | blast_aggregator tests (red) | 11 | 1 new |
| 2 | blast_aggregator service (green) | — | 1 new |
| 3 | Email template | — | 1 new |
| 4 | compose_monthly_blast tests (red) | 13 | 1 new |
| 5 | compose_monthly_blast command (green) | — | 1 new (+2 __init__.py if needed) |
| 6 | Full test suite verification | — | fixes if needed |
| 7 | Documentation | — | 2 modified |

**Total: ~24 new tests, 5 new files, 2 modified files**
