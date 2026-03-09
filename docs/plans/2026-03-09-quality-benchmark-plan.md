# Quality Benchmark Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a `benchmark_quality` management command that evaluates all existing mentions, briefs, and reports, saving results to a JSON file for before/after comparison across pipeline rebuilds.

**Architecture:** A single management command queries production data, runs deterministic + Gemini evaluations, and writes a timestamped JSON benchmark file with both summary stats and per-item detail.

**Tech Stack:** Django management command, existing evaluator service (evaluator.py), Gemini API for brief/report evaluation.

---

### Task 1: Create the benchmark service module

**Files:**
- Create: `backend/parliament/services/benchmark.py`
- Test: `backend/parliament/tests/test_benchmark.py`

**Step 1: Write the failing test**

```python
# backend/parliament/tests/test_benchmark.py
import datetime
from unittest.mock import patch

from django.test import TestCase

from hansard.models import HansardMention, HansardSitting
from parliament.models import ParliamentaryMeeting, SittingBrief
from parliament.services.benchmark import benchmark_mentions


class BenchmarkMentionsTest(TestCase):
    def setUp(self):
        self.sitting = HansardSitting.objects.create(
            sitting_date=datetime.date(2099, 1, 1),
            pdf_url="https://example.com/test.pdf",
            pdf_filename="test.pdf",
            status="COMPLETED",
        )
        self.mention = HansardMention.objects.create(
            sitting=self.sitting,
            verbatim_quote="YB Sivakumar mentioned SJK(T) Ladang Bikam needs repairs",
            context_before="Tuan Yang di-Pertua,",
            mp_name="Sivakumar",
            mention_type="INFRASTRUCTURE",
            significance=3,
            ai_summary="MP discussed school repairs",
            speaker_verified=True,
            eval_warnings=[],
            eval_confidence=1.0,
        )

    def test_benchmark_mentions_returns_list(self):
        results = benchmark_mentions()
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 1)

    def test_benchmark_mention_has_deterministic_fields(self):
        results = benchmark_mentions()
        item = results[0]
        self.assertIn("mention_id", item)
        self.assertIn("sitting_date", item)
        self.assertIn("mp_name", item)
        self.assertIn("deterministic", item)
        det = item["deterministic"]
        self.assertIn("speaker_verified", det)
        self.assertIn("confidence", det)
        self.assertIn("warnings", det)

    def test_benchmark_mention_has_gemini_field(self):
        results = benchmark_mentions(use_gemini=True)
        item = results[0]
        self.assertIn("gemini", item)
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest parliament/tests/test_benchmark.py -v`
Expected: FAIL — `ImportError: cannot import name 'benchmark_mentions'`

**Step 3: Write the benchmark_mentions function**

```python
# backend/parliament/services/benchmark.py
"""Quality benchmark service — snapshots current output quality for comparison."""

import logging

from hansard.models import HansardMention
from parliament.services.evaluator import evaluate_mention

logger = logging.getLogger(__name__)


def benchmark_mentions(use_gemini=False):
    """Run deterministic quality checks on all analysed mentions.

    Args:
        use_gemini: If True, also run Gemini evaluation (costs API calls).

    Returns:
        List of dicts with mention_id, sitting_date, mp_name,
        deterministic results, and optionally gemini results.
    """
    mentions = (
        HansardMention.objects
        .exclude(ai_summary="")
        .select_related("sitting")
        .order_by("sitting__sitting_date", "id")
    )

    results = []
    for mention in mentions:
        result = evaluate_mention(mention)
        item = {
            "mention_id": mention.id,
            "sitting_date": str(mention.sitting.sitting_date),
            "mp_name": mention.mp_name,
            "mention_type": mention.mention_type,
            "significance": mention.significance,
            "deterministic": {
                "speaker_verified": mention.speaker_verified,
                "confidence": result.confidence,
                "warnings": result.warnings,
            },
        }

        if use_gemini:
            item["gemini"] = {"note": "not yet implemented"}

        results.append(item)

    return results
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest parliament/tests/test_benchmark.py::BenchmarkMentionsTest -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/parliament/services/benchmark.py backend/parliament/tests/test_benchmark.py
git commit -m "feat: add benchmark_mentions service for quality snapshots"
```

---

### Task 2: Add benchmark_briefs and benchmark_reports functions

**Files:**
- Modify: `backend/parliament/services/benchmark.py`
- Modify: `backend/parliament/tests/test_benchmark.py`

**Step 1: Write the failing tests**

Add to `test_benchmark.py`:

```python
from parliament.services.benchmark import benchmark_briefs, benchmark_reports


class BenchmarkBriefsTest(TestCase):
    def setUp(self):
        self.sitting = HansardSitting.objects.create(
            sitting_date=datetime.date(2099, 2, 1),
            pdf_url="https://example.com/test2.pdf",
            pdf_filename="test2.pdf",
            status="COMPLETED",
        )
        self.mention = HansardMention.objects.create(
            sitting=self.sitting,
            verbatim_quote="Discussion about SJK(T) schools",
            mp_name="Test MP",
            ai_summary="Test summary about Tamil schools",
        )
        self.brief = SittingBrief.objects.create(
            sitting=self.sitting,
            title="Test Brief",
            summary_html="<p>Test brief content about SJK(T) Ladang Bikam</p>",
            quality_flag="GREEN",
        )

    @patch("parliament.services.benchmark.evaluate_brief")
    def test_benchmark_briefs_returns_list(self, mock_eval_fn):
        from parliament.services.evaluator import EvaluationResult
        mock_eval_fn.return_value = EvaluationResult(
            verdict="PASS",
            tier1_results={"fabricated_facts": {"pass": True}},
            tier2_scores={"school_linkification": {"score": 8}},
            tier3_flags={"tone_drift": "OK"},
        )
        results = benchmark_briefs()
        self.assertEqual(len(results), 1)
        self.assertIn("brief_id", results[0])
        self.assertIn("sitting_date", results[0])
        self.assertIn("evaluation", results[0])
        self.assertEqual(results[0]["evaluation"]["verdict"], "PASS")


class BenchmarkReportsTest(TestCase):
    def setUp(self):
        self.meeting = ParliamentaryMeeting.objects.create(
            name="Test Meeting",
            short_name="Test 2099",
            term=99, session=1, year=2099,
            start_date="2099-03-01",
            end_date="2099-03-31",
            report_html="<h2>Test Report</h2><p>Content</p>",
            quality_flag="GREEN",
        )

    @patch("parliament.services.benchmark.evaluate_report")
    def test_benchmark_reports_returns_list(self, mock_eval_fn):
        from parliament.services.evaluator import EvaluationResult
        mock_eval_fn.return_value = EvaluationResult(
            verdict="PASS",
            tier1_results={"fabricated_facts": {"pass": True}},
            tier2_scores={"headline_specificity": {"score": 9}},
            tier3_flags={"tone_drift": "OK"},
        )
        results = benchmark_reports()
        self.assertEqual(len(results), 1)
        self.assertIn("meeting_id", results[0])
        self.assertIn("short_name", results[0])
        self.assertIn("evaluation", results[0])
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest parliament/tests/test_benchmark.py -v`
Expected: FAIL — `ImportError: cannot import name 'benchmark_briefs'`

**Step 3: Add benchmark_briefs and benchmark_reports**

Add to `backend/parliament/services/benchmark.py`:

```python
from parliament.models import ParliamentaryMeeting, SittingBrief, MP
from parliament.services.evaluator import (
    evaluate_brief, evaluate_mention, evaluate_report, EvaluationResult,
)
from schools.models import School


def _get_school_and_mp_names():
    """Get school and MP name lists for evaluator calls."""
    school_names = list(School.objects.values_list("name", flat=True)[:100])
    mp_names = list(MP.objects.values_list("name", flat=True)[:50])
    return school_names, mp_names


def _result_to_dict(result: EvaluationResult) -> dict:
    """Convert EvaluationResult to a JSON-serialisable dict."""
    return {
        "verdict": result.verdict,
        "tier1_results": result.tier1_results,
        "tier2_scores": result.tier2_scores,
        "tier3_flags": result.tier3_flags,
        "unlinked_schools": result.unlinked_schools,
        "repair_suggestions": result.repair_suggestions,
        "evaluator_error": result.evaluator_error,
    }


def benchmark_briefs():
    """Run Gemini evaluation on all briefs with content.

    Returns:
        List of dicts with brief_id, sitting_date, title, quality_flag, evaluation.
    """
    school_names, mp_names = _get_school_and_mp_names()
    briefs = (
        SittingBrief.objects
        .exclude(summary_html="")
        .select_related("sitting")
        .order_by("sitting__sitting_date")
    )

    results = []
    for brief in briefs:
        mentions = brief.sitting.mentions.exclude(ai_summary="")
        source_summaries = "\n".join(m.ai_summary for m in mentions)

        result = evaluate_brief(
            brief_html=brief.summary_html,
            source_summaries=source_summaries,
            school_names=school_names,
            mp_names=mp_names,
        )

        results.append({
            "brief_id": brief.id,
            "sitting_date": str(brief.sitting.sitting_date),
            "title": brief.title,
            "quality_flag": brief.quality_flag,
            "word_count": len(brief.summary_html.split()),
            "evaluation": _result_to_dict(result),
        })

        logger.info(
            "Brief %s (%s): %s",
            brief.id, brief.sitting.sitting_date, result.verdict,
        )

    return results


def benchmark_reports():
    """Run Gemini evaluation on all meeting reports with content.

    Returns:
        List of dicts with meeting_id, short_name, quality_flag, evaluation.
    """
    school_names, mp_names = _get_school_and_mp_names()
    meetings = (
        ParliamentaryMeeting.objects
        .exclude(report_html="")
        .order_by("start_date")
    )

    results = []
    for meeting in meetings:
        briefs = SittingBrief.objects.filter(
            sitting__meeting=meeting,
        ).exclude(summary_html="")
        source_briefs = "\n\n---\n\n".join(
            b.summary_html for b in briefs
        )

        result = evaluate_report(
            report_html=meeting.report_html,
            source_briefs=source_briefs,
            school_names=school_names,
            mp_names=mp_names,
        )

        results.append({
            "meeting_id": meeting.id,
            "short_name": meeting.short_name,
            "quality_flag": meeting.quality_flag,
            "word_count": len(meeting.report_html.split()),
            "evaluation": _result_to_dict(result),
        })

        logger.info(
            "Report %s (%s): %s",
            meeting.id, meeting.short_name, result.verdict,
        )

    return results
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest parliament/tests/test_benchmark.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/parliament/services/benchmark.py backend/parliament/tests/test_benchmark.py
git commit -m "feat: add benchmark_briefs and benchmark_reports functions"
```

---

### Task 3: Add build_benchmark_report summary function

**Files:**
- Modify: `backend/parliament/services/benchmark.py`
- Modify: `backend/parliament/tests/test_benchmark.py`

**Step 1: Write the failing test**

```python
from parliament.services.benchmark import build_benchmark_report


class BuildBenchmarkReportTest(TestCase):
    def test_empty_data_produces_valid_structure(self):
        report = build_benchmark_report(
            label="test",
            mention_results=[],
            brief_results=[],
            report_results=[],
        )
        self.assertIn("meta", report)
        self.assertIn("summary", report)
        self.assertIn("mentions", report)
        self.assertIn("briefs", report)
        self.assertIn("reports", report)
        self.assertEqual(report["meta"]["label"], "test")

    def test_summary_computes_averages(self):
        mention_results = [
            {"mention_id": 1, "deterministic": {"confidence": 0.8, "warnings": ["warn1"]}},
            {"mention_id": 2, "deterministic": {"confidence": 1.0, "warnings": []}},
        ]
        brief_results = [
            {"brief_id": 1, "evaluation": {"verdict": "PASS", "tier2_scores": {"accuracy": {"score": 8}}}},
        ]
        report_results = [
            {"meeting_id": 1, "evaluation": {"verdict": "FIX", "tier2_scores": {"headline": {"score": 6}}}},
        ]
        report = build_benchmark_report("test", mention_results, brief_results, report_results)
        summary = report["summary"]

        self.assertEqual(summary["mentions"]["total"], 2)
        self.assertAlmostEqual(summary["mentions"]["avg_confidence"], 0.9)
        self.assertEqual(summary["mentions"]["with_warnings"], 1)
        self.assertEqual(summary["briefs"]["total"], 1)
        self.assertEqual(summary["briefs"]["verdicts"]["PASS"], 1)
        self.assertEqual(summary["reports"]["total"], 1)
        self.assertEqual(summary["reports"]["verdicts"]["FIX"], 1)
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest parliament/tests/test_benchmark.py::BuildBenchmarkReportTest -v`
Expected: FAIL — `ImportError`

**Step 3: Write build_benchmark_report**

Add to `benchmark.py`:

```python
from datetime import datetime


def build_benchmark_report(label, mention_results, brief_results, report_results):
    """Build the full benchmark JSON structure with summary + per-item detail.

    Args:
        label: Human-readable label (e.g. "pre-rebuild", "post-rebuild-1st-2026")
        mention_results: From benchmark_mentions()
        brief_results: From benchmark_briefs()
        report_results: From benchmark_reports()

    Returns:
        Dict ready for json.dump().
    """
    # Mention summary
    confidences = [m["deterministic"]["confidence"] for m in mention_results]
    warned = [m for m in mention_results if m["deterministic"]["warnings"]]

    mention_summary = {
        "total": len(mention_results),
        "avg_confidence": round(sum(confidences) / len(confidences), 3) if confidences else 0,
        "with_warnings": len(warned),
    }

    # Brief summary
    brief_verdicts = {}
    brief_tier2_avgs = {}
    for b in brief_results:
        v = b["evaluation"]["verdict"]
        brief_verdicts[v] = brief_verdicts.get(v, 0) + 1
        for criterion, data in b["evaluation"].get("tier2_scores", {}).items():
            if "score" in data:
                brief_tier2_avgs.setdefault(criterion, []).append(data["score"])

    brief_summary = {
        "total": len(brief_results),
        "verdicts": brief_verdicts,
        "avg_tier2": {k: round(sum(v) / len(v), 1) for k, v in brief_tier2_avgs.items()},
    }

    # Report summary
    report_verdicts = {}
    report_tier2_avgs = {}
    for r in report_results:
        v = r["evaluation"]["verdict"]
        report_verdicts[v] = report_verdicts.get(v, 0) + 1
        for criterion, data in r["evaluation"].get("tier2_scores", {}).items():
            if "score" in data:
                report_tier2_avgs.setdefault(criterion, []).append(data["score"])

    report_summary = {
        "total": len(report_results),
        "verdicts": report_verdicts,
        "avg_tier2": {k: round(sum(v) / len(v), 1) for k, v in report_tier2_avgs.items()},
    }

    return {
        "meta": {
            "label": label,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "evaluator_version": "v1",
        },
        "summary": {
            "mentions": mention_summary,
            "briefs": brief_summary,
            "reports": report_summary,
        },
        "mentions": mention_results,
        "briefs": brief_results,
        "reports": report_results,
    }
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest parliament/tests/test_benchmark.py::BuildBenchmarkReportTest -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/parliament/services/benchmark.py backend/parliament/tests/test_benchmark.py
git commit -m "feat: add build_benchmark_report summary builder"
```

---

### Task 4: Create the management command

**Files:**
- Create: `backend/parliament/management/commands/benchmark_quality.py`
- Modify: `backend/parliament/tests/test_benchmark.py`

**Step 1: Write the failing test**

```python
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command


class BenchmarkQualityCommandTest(TestCase):
    @patch("parliament.services.benchmark.benchmark_reports")
    @patch("parliament.services.benchmark.benchmark_briefs")
    @patch("parliament.services.benchmark.benchmark_mentions")
    def test_command_runs_and_writes_file(self, mock_mentions, mock_briefs, mock_reports):
        mock_mentions.return_value = []
        mock_briefs.return_value = []
        mock_reports.return_value = []

        out = StringIO()
        call_command("benchmark_quality", "--label", "test-run", stdout=out)
        output = out.getvalue()
        self.assertIn("Benchmark saved", output)
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest parliament/tests/test_benchmark.py::BenchmarkQualityCommandTest -v`
Expected: FAIL — command not found

**Step 3: Create the management command**

```python
# backend/parliament/management/commands/benchmark_quality.py
"""Benchmark current quality of all mentions, briefs, and reports.

Usage:
    python manage.py benchmark_quality --label pre-rebuild
    python manage.py benchmark_quality --label post-rebuild --mentions-only
"""

import json
import logging
import os
from datetime import datetime

from django.core.management.base import BaseCommand

from parliament.services.benchmark import (
    benchmark_briefs,
    benchmark_mentions,
    benchmark_reports,
    build_benchmark_report,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Snapshot quality of all mentions, briefs, and reports to a JSON benchmark file."

    def add_arguments(self, parser):
        parser.add_argument(
            "--label",
            required=True,
            help="Label for this benchmark run (e.g. pre-rebuild, post-rebuild-1st-2026)",
        )
        parser.add_argument(
            "--mentions-only",
            action="store_true",
            help="Only benchmark mentions (no Gemini API calls)",
        )
        parser.add_argument(
            "--output-dir",
            default="",
            help="Output directory (default: docs/quality/)",
        )

    def handle(self, **options):
        label = options["label"]
        mentions_only = options["mentions_only"]
        output_dir = options["output_dir"] or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ))),
            "docs", "quality",
        )

        os.makedirs(output_dir, exist_ok=True)

        # 1. Mentions (deterministic — no API cost)
        self.stdout.write("Evaluating mentions (deterministic)...")
        mention_results = benchmark_mentions()
        self.stdout.write(f"  {len(mention_results)} mentions evaluated")

        # 2. Briefs and reports (Gemini API calls)
        brief_results = []
        report_results = []
        if not mentions_only:
            self.stdout.write("Evaluating briefs (Gemini API)...")
            brief_results = benchmark_briefs()
            self.stdout.write(f"  {len(brief_results)} briefs evaluated")

            self.stdout.write("Evaluating reports (Gemini API)...")
            report_results = benchmark_reports()
            self.stdout.write(f"  {len(report_results)} reports evaluated")

        # 3. Build and save
        report = build_benchmark_report(
            label=label,
            mention_results=mention_results,
            brief_results=brief_results,
            report_results=report_results,
        )

        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        filename = f"benchmark-{date_str}-{label}.json"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        self.stdout.write(self.style.SUCCESS(
            f"Benchmark saved to {filepath}"
        ))

        # Print summary
        summary = report["summary"]
        self.stdout.write(f"\n--- Summary ---")
        self.stdout.write(
            f"Mentions: {summary['mentions']['total']} total, "
            f"avg confidence {summary['mentions']['avg_confidence']}, "
            f"{summary['mentions']['with_warnings']} with warnings"
        )
        if brief_results:
            self.stdout.write(
                f"Briefs: {summary['briefs']['total']} total, "
                f"verdicts: {summary['briefs']['verdicts']}"
            )
        if report_results:
            self.stdout.write(
                f"Reports: {summary['reports']['total']} total, "
                f"verdicts: {summary['reports']['verdicts']}"
            )
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest parliament/tests/test_benchmark.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add backend/parliament/management/commands/benchmark_quality.py backend/parliament/tests/test_benchmark.py
git commit -m "feat: add benchmark_quality management command"
```

---

### Task 5: Run pre-rebuild benchmark on production data

**Step 1: Create the output directory**

```bash
mkdir -p docs/quality
```

**Step 2: Run mentions-only benchmark first (no API cost)**

```bash
cd backend
DATABASE_URL="postgresql://postgres.kafuxsinrbqafvarckxu:%3FFJ%2B7FTwXKK65Lw@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres" \
python manage.py benchmark_quality --label pre-rebuild --mentions-only
```

Expected: JSON file created at `docs/quality/benchmark-2026-03-09-pre-rebuild.json` with ~184 mention evaluations.

**Step 3: Run full benchmark (mentions + briefs + reports)**

```bash
cd backend
DATABASE_URL="postgresql://postgres.kafuxsinrbqafvarckxu:%3FFJ%2B7FTwXKK65Lw@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres" \
GEMINI_API_KEY="$GEMINI_API_KEY" \
python manage.py benchmark_quality --label pre-rebuild
```

Expected: JSON file with ~184 mention + ~71 brief + ~11 report evaluations. ~82 Gemini API calls.

**Step 4: Commit the benchmark file**

```bash
git add docs/quality/
git commit -m "docs: add pre-rebuild quality benchmark"
```

---

## Estimated API Usage

| Content Type | Count | Gemini Calls | Notes |
|-------------|-------|-------------|-------|
| Mentions | ~184 | 0 | Deterministic only |
| Briefs | ~71 | ~71 | 1 call per brief |
| Reports | ~11 | ~11 | 1 call per report |
| **Total** | | **~82** | Well within Tier 1 (10K RPD) |
