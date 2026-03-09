"""Tests for the quality benchmark service.

Covers: benchmark_mentions, benchmark_briefs, benchmark_reports,
build_benchmark_report, helper functions, and the benchmark_quality command.
"""

import tempfile
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from hansard.models import HansardMention, HansardSitting
from parliament.models import ParliamentaryMeeting, SittingBrief
from parliament.services.evaluator import EvaluationResult


class BenchmarkMentionsTest(TestCase):
    """Test benchmark_mentions() — deterministic mention evaluation."""

    def setUp(self):
        self.sitting = HansardSitting.objects.create(
            sitting_date="2097-01-10",
            pdf_url="https://example.com/bm.pdf",
            pdf_filename="bm.pdf",
            status="COMPLETED",
        )
        self.mention = HansardMention.objects.create(
            sitting=self.sitting,
            verbatim_quote=(
                "YB Arul [Segamat] asked about SJK(T) Ladang Bikam "
                "funding of RM2 million for infrastructure repairs."
            ),
            context_before="",
            page_number=1,
            mp_name="YB Arul",
            mp_constituency="Segamat",
            mention_type="BUDGET",
            significance=4,
            ai_summary="MP requests RM2M for SJK(T) Ladang Bikam.",
            speaker_verified=True,
        )

    def test_returns_list(self):
        from parliament.services.benchmark import benchmark_mentions

        results = benchmark_mentions()
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 1)

    def test_has_correct_fields(self):
        from parliament.services.benchmark import benchmark_mentions

        results = benchmark_mentions()
        item = results[0]
        self.assertIn("mention_id", item)
        self.assertIn("sitting_date", item)
        self.assertIn("mp_name", item)
        self.assertIn("mention_type", item)
        self.assertIn("significance", item)
        self.assertIn("deterministic", item)
        self.assertIn("speaker_verified", item["deterministic"])
        self.assertIn("confidence", item["deterministic"])
        self.assertIn("warnings", item["deterministic"])
        self.assertEqual(item["mention_id"], self.mention.id)
        self.assertEqual(item["mp_name"], "YB Arul")

    def test_gemini_field_when_use_gemini_true(self):
        from parliament.services.benchmark import benchmark_mentions

        results = benchmark_mentions(use_gemini=True)
        item = results[0]
        self.assertIn("gemini", item)
        self.assertEqual(item["gemini"]["note"], "not yet implemented")

    def test_gemini_field_absent_when_use_gemini_false(self):
        from parliament.services.benchmark import benchmark_mentions

        results = benchmark_mentions(use_gemini=False)
        item = results[0]
        self.assertNotIn("gemini", item)

    def test_skips_mentions_without_ai_summary(self):
        from parliament.services.benchmark import benchmark_mentions

        # Create a mention with empty ai_summary
        HansardMention.objects.create(
            sitting=self.sitting,
            verbatim_quote="SJK(T) mentioned.",
            context_before="",
            page_number=2,
            ai_summary="",  # empty — should be skipped
        )
        results = benchmark_mentions()
        self.assertEqual(len(results), 1)  # only the setUp mention


class BenchmarkBriefsTest(TestCase):
    """Test benchmark_briefs() — mocked evaluate_brief."""

    def setUp(self):
        self.sitting = HansardSitting.objects.create(
            sitting_date="2097-02-10",
            pdf_url="https://example.com/bb.pdf",
            pdf_filename="bb.pdf",
            status="COMPLETED",
        )
        HansardMention.objects.create(
            sitting=self.sitting,
            verbatim_quote="Budget mention for SJK(T) Ladang Bikam.",
            context_before="",
            page_number=5,
            mp_name="YB Test",
            ai_summary="Test summary for benchmark.",
            review_status="APPROVED",
        )
        self.brief = SittingBrief.objects.create(
            sitting=self.sitting,
            title="Brief for 2097-02-10",
            summary_html="<p>Brief content here</p>",
        )

    @patch("parliament.services.benchmark.evaluate_brief")
    def test_returns_list_with_correct_fields(self, mock_eval):
        mock_eval.return_value = EvaluationResult(
            verdict="PASS",
            tier1_results={"fabricated_facts": {"pass": True}},
            tier2_scores={"school_linkification": {"score": 9, "feedback": None}},
            tier3_flags={"tone_drift": "OK"},
        )

        from parliament.services.benchmark import benchmark_briefs

        results = benchmark_briefs()
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 1)

        item = results[0]
        self.assertIn("brief_id", item)
        self.assertIn("sitting_date", item)
        self.assertIn("title", item)
        self.assertIn("quality_flag", item)
        self.assertIn("word_count", item)
        self.assertIn("evaluation", item)
        self.assertEqual(item["brief_id"], self.brief.id)
        self.assertEqual(item["title"], "Brief for 2097-02-10")

    @patch("parliament.services.benchmark.evaluate_brief")
    def test_evaluation_dict_structure(self, mock_eval):
        mock_eval.return_value = EvaluationResult(
            verdict="FIX",
            tier1_results={"fabricated_facts": {"pass": True}},
            tier2_scores={"school_linkification": {"score": 5, "feedback": "Needs links"}},
            tier3_flags={"tone_drift": "MILD"},
            repair_suggestions=["Add school links"],
        )

        from parliament.services.benchmark import benchmark_briefs

        results = benchmark_briefs()
        ev = results[0]["evaluation"]
        self.assertEqual(ev["verdict"], "FIX")
        self.assertIn("tier1_results", ev)
        self.assertIn("tier2_scores", ev)
        self.assertIn("tier3_flags", ev)
        self.assertIn("repair_suggestions", ev)

    @patch("parliament.services.benchmark.evaluate_brief")
    def test_skips_briefs_without_summary_html(self, mock_eval):
        # Create a brief with empty summary_html
        sitting2 = HansardSitting.objects.create(
            sitting_date="2097-02-11",
            pdf_url="https://example.com/bb2.pdf",
            pdf_filename="bb2.pdf",
            status="COMPLETED",
        )
        SittingBrief.objects.create(
            sitting=sitting2,
            title="Empty Brief",
            summary_html="",  # empty — should be skipped
        )

        mock_eval.return_value = EvaluationResult(verdict="PASS")

        from parliament.services.benchmark import benchmark_briefs

        results = benchmark_briefs()
        self.assertEqual(len(results), 1)


class BenchmarkReportsTest(TestCase):
    """Test benchmark_reports() — mocked evaluate_report."""

    def setUp(self):
        self.meeting = ParliamentaryMeeting.objects.create(
            name="Benchmark Meeting",
            short_name="BM 2097",
            term=90, session=1, year=2097,
            start_date="2097-03-01",
            end_date="2097-03-28",
            report_html="<h2>Report</h2><p>Content here</p>",
        )
        # Create a sitting + brief linked to this meeting
        self.sitting = HansardSitting.objects.create(
            sitting_date="2097-03-10",
            pdf_url="https://example.com/br.pdf",
            pdf_filename="br.pdf",
            status="COMPLETED",
            meeting=self.meeting,
        )
        SittingBrief.objects.create(
            sitting=self.sitting,
            title="Brief for report test",
            summary_html="<p>Source brief content</p>",
        )

    @patch("parliament.services.benchmark.evaluate_report")
    def test_returns_list_with_correct_fields(self, mock_eval):
        mock_eval.return_value = EvaluationResult(
            verdict="PASS",
            tier1_results={"fabricated_facts": {"pass": True}},
            tier2_scores={"headline_specificity": {"score": 8}},
            tier3_flags={"tone_drift": "OK"},
        )

        from parliament.services.benchmark import benchmark_reports

        results = benchmark_reports()
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 1)

        item = results[0]
        self.assertIn("meeting_id", item)
        self.assertIn("short_name", item)
        self.assertIn("quality_flag", item)
        self.assertIn("word_count", item)
        self.assertIn("evaluation", item)
        self.assertEqual(item["meeting_id"], self.meeting.id)
        self.assertEqual(item["short_name"], "BM 2097")

    @patch("parliament.services.benchmark.evaluate_report")
    def test_skips_meetings_without_report_html(self, mock_eval):
        ParliamentaryMeeting.objects.create(
            name="Empty Report Meeting",
            short_name="ER 2097",
            term=91, session=1, year=2097,
            start_date="2097-04-01",
            end_date="2097-04-28",
            report_html="",  # empty — should be skipped
        )
        mock_eval.return_value = EvaluationResult(verdict="PASS")

        from parliament.services.benchmark import benchmark_reports

        results = benchmark_reports()
        self.assertEqual(len(results), 1)

    @patch("parliament.services.benchmark.evaluate_report")
    def test_evaluation_dict_structure(self, mock_eval):
        mock_eval.return_value = EvaluationResult(
            verdict="REJECT",
            tier1_results={"hallucinated_schools": {"pass": False, "details": "Bad"}},
            tier2_scores={},
            tier3_flags={},
            unlinked_schools=["SJK(T) Phantom"],
            repair_suggestions=["Remove phantom school"],
        )

        from parliament.services.benchmark import benchmark_reports

        results = benchmark_reports()
        ev = results[0]["evaluation"]
        self.assertEqual(ev["verdict"], "REJECT")
        self.assertIn("unlinked_schools", ev)
        self.assertEqual(ev["unlinked_schools"], ["SJK(T) Phantom"])


class BuildBenchmarkReportTest(TestCase):
    """Test build_benchmark_report() — summary computation."""

    def test_empty_data_structure(self):
        from parliament.services.benchmark import build_benchmark_report

        report = build_benchmark_report(
            label="empty-run",
            mention_results=[],
            brief_results=[],
            report_results=[],
        )
        self.assertIn("meta", report)
        self.assertIn("summary", report)
        self.assertIn("detail", report)
        self.assertEqual(report["meta"]["label"], "empty-run")
        self.assertIn("timestamp", report["meta"])
        self.assertEqual(report["summary"]["mentions"]["total"], 0)
        self.assertEqual(report["summary"]["briefs"]["total"], 0)
        self.assertEqual(report["summary"]["reports"]["total"], 0)

    def test_summary_computation(self):
        from parliament.services.benchmark import build_benchmark_report

        mention_results = [
            {
                "mention_id": 1,
                "sitting_date": "2097-01-10",
                "mp_name": "YB A",
                "mention_type": "BUDGET",
                "significance": 4,
                "deterministic": {
                    "speaker_verified": True,
                    "confidence": 0.85,
                    "warnings": ["warn1"],
                },
            },
            {
                "mention_id": 2,
                "sitting_date": "2097-01-11",
                "mp_name": "YB B",
                "mention_type": "OTHER",
                "significance": 2,
                "deterministic": {
                    "speaker_verified": True,
                    "confidence": 1.0,
                    "warnings": [],
                },
            },
        ]
        brief_results = [
            {
                "brief_id": 1,
                "sitting_date": "2097-01-10",
                "title": "Brief 1",
                "quality_flag": "GREEN",
                "word_count": 200,
                "evaluation": {
                    "verdict": "PASS",
                    "tier2_scores": {
                        "school_linkification": {"score": 9},
                        "factual_traceability": {"score": 8},
                    },
                },
            },
        ]
        report_results = [
            {
                "meeting_id": 1,
                "short_name": "1st Meeting",
                "quality_flag": "AMBER",
                "word_count": 500,
                "evaluation": {
                    "verdict": "FIX",
                    "tier2_scores": {
                        "headline_specificity": {"score": 5},
                        "actionability": {"score": 7},
                    },
                },
            },
        ]

        report = build_benchmark_report(
            label="test-run",
            mention_results=mention_results,
            brief_results=brief_results,
            report_results=report_results,
        )

        # Mentions summary
        ms = report["summary"]["mentions"]
        self.assertEqual(ms["total"], 2)
        self.assertAlmostEqual(ms["avg_confidence"], 0.925)
        self.assertEqual(ms["with_warnings"], 1)

        # Briefs summary
        bs = report["summary"]["briefs"]
        self.assertEqual(bs["total"], 1)
        self.assertEqual(bs["verdicts"]["PASS"], 1)
        self.assertIn("avg_tier2", bs)

        # Reports summary
        rs = report["summary"]["reports"]
        self.assertEqual(rs["total"], 1)
        self.assertEqual(rs["verdicts"]["FIX"], 1)
        self.assertIn("avg_tier2", rs)

        # Detail section
        self.assertEqual(len(report["detail"]["mentions"]), 2)
        self.assertEqual(len(report["detail"]["briefs"]), 1)
        self.assertEqual(len(report["detail"]["reports"]), 1)


class BenchmarkQualityCommandTest(TestCase):
    """Test the benchmark_quality management command."""

    @patch("parliament.services.benchmark.benchmark_reports")
    @patch("parliament.services.benchmark.benchmark_briefs")
    @patch("parliament.services.benchmark.benchmark_mentions")
    def test_command_runs_and_writes_file(self, mock_mentions, mock_briefs, mock_reports):
        mock_mentions.return_value = []
        mock_briefs.return_value = []
        mock_reports.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            out = StringIO()
            call_command(
                "benchmark_quality",
                "--label", "test-run",
                "--output-dir", tmpdir,
                stdout=out,
            )
            output = out.getvalue()
            self.assertIn("Benchmark saved", output)

    @patch("parliament.services.benchmark.benchmark_mentions")
    def test_mentions_only_skips_api_calls(self, mock_mentions):
        mock_mentions.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            out = StringIO()
            call_command(
                "benchmark_quality",
                "--label", "mentions-only-test",
                "--mentions-only",
                "--output-dir", tmpdir,
                stdout=out,
            )
            output = out.getvalue()
            self.assertIn("Benchmark saved", output)
            self.assertNotIn("Evaluating briefs", output)
