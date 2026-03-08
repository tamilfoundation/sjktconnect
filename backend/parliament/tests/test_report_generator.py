"""Tests for generate_meeting_reports command with quality loop."""

import json
from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import TestCase

from hansard.models import HansardSitting
from parliament.models import ParliamentaryMeeting, QualityLog, SittingBrief


def _make_meeting_with_briefs():
    """Helper: create a meeting with sitting + brief."""
    meeting = ParliamentaryMeeting.objects.create(
        name="Test Meeting for Reports",
        short_name="Test Meeting",
        term=99, session=1, year=2099,
        start_date="2099-02-24", end_date="2099-04-10",
    )
    sitting = HansardSitting.objects.create(
        sitting_date="2099-02-24",
        pdf_url="https://example.com/test.pdf",
        pdf_filename="test.pdf",
        meeting=meeting,
        mention_count=3,
    )

    SittingBrief.objects.create(
        sitting=sitting,
        title="3 Tamil School Mentions",
        summary_html="<p>YB Arul requests RM2M for SJK(T) Ladang Bikam.</p>",
    )
    return meeting


SAMPLE_REPORT_MD = (
    "## PM Pledges Aid for Tamil Schools\n\n"
    "Key development this meeting.\n\n"
    "## Key Findings\n\n- RM2M allocated\n\n"
    "## MP Scorecard\n\n| MP | Constituency | Topic | Stance | Impact |\n"
    "| --- | --- | --- | --- | --- |\n"
    "| YB Arul | Segamat | Budget | Advocacy | Budget Allocation |\n\n"
    "## What to Watch\n\n- Track the RM2M commitment"
)


class DryRunTests(TestCase):

    def test_dry_run_no_api_call(self):
        _make_meeting_with_briefs()
        out = StringIO()
        call_command("generate_meeting_reports", "--dry-run", stdout=out)
        output = out.getvalue()
        self.assertIn("Test Meeting", output)


class HtmlToPlainTests(TestCase):

    def test_strips_tags(self):
        from parliament.management.commands.generate_meeting_reports import html_to_plain
        result = html_to_plain("<p>Hello <b>world</b></p>")
        self.assertIn("Hello", result)
        self.assertIn("world", result)
        self.assertNotIn("<p>", result)

    def test_decodes_entities(self):
        from parliament.management.commands.generate_meeting_reports import html_to_plain
        result = html_to_plain("&amp; &lt;")
        self.assertIn("&", result)
        self.assertIn("<", result)


class LinkifySchoolsTests(TestCase):

    def test_links_known_school(self):
        from parliament.management.commands.generate_meeting_reports import _linkify_schools
        from schools.models import School
        School.objects.create(
            moe_code="ZZZ9999",
            name="Sekolah Jenis Kebangsaan (Tamil) Ladang Testville",
            short_name="SJK(T) Ladang Testville",
            state="Pahang", ppd="Temerloh",
        )
        html = "<p>SJK(T) Ladang Testville needs repairs</p>"
        result = _linkify_schools(html)
        self.assertIn("ZZZ9999", result)
        self.assertIn("<a href=", result)

    def test_skips_unknown_school(self):
        from parliament.management.commands.generate_meeting_reports import _linkify_schools
        html = "<p>SJK(T) Nonexistent School</p>"
        result = _linkify_schools(html)
        self.assertNotIn("<a href=", result)


class NormalisePlaceNameTests(TestCase):

    def test_tanjong_matches_tanjung(self):
        from parliament.management.commands.generate_meeting_reports import _normalise_place_name
        self.assertEqual(_normalise_place_name("Tanjong Piai"), _normalise_place_name("Tanjung Piai"))

    def test_sungei_matches_sungai(self):
        from parliament.management.commands.generate_meeting_reports import _normalise_place_name
        self.assertEqual(_normalise_place_name("Sungei Siput"), _normalise_place_name("Sungai Siput"))


class LinkifyConstituencyVariantTests(TestCase):

    def test_tanjong_links_to_tanjung(self):
        from parliament.management.commands.generate_meeting_reports import _linkify_constituencies
        from schools.models import Constituency
        Constituency.objects.create(name="Tanjung Piai", code="P165", state="Johor")
        html = '<td style="text-align: left;">Tanjong Piai</td>'
        result = _linkify_constituencies(html)
        self.assertIn("P165", result)
        self.assertIn("<a href=", result)


class LinkifyBriefsTests(TestCase):

    def test_links_sitting_date_to_brief_detail(self):
        from parliament.management.commands.generate_meeting_reports import _linkify_briefs
        meeting = ParliamentaryMeeting.objects.create(
            name="Test", short_name="Test",
            term=99, session=1, year=2099,
            start_date="2099-02-24", end_date="2099-04-10",
        )
        sitting = HansardSitting.objects.create(
            sitting_date="2099-02-24",
            pdf_url="https://example.com/test.pdf",
            pdf_filename="test.pdf",
            meeting=meeting,
        )
        brief = SittingBrief.objects.create(
            sitting=sitting,
            title="Test Brief",
            summary_html="<p>Test</p>",
        )
        html = "<p>On 24 February 2099, MPs raised issues.</p>"
        result = _linkify_briefs(html, meeting)
        self.assertIn(f"/parliament-watch/sittings/{brief.pk}", result)
        self.assertIn("<a href=", result)

    def test_skips_if_no_date_match(self):
        from parliament.management.commands.generate_meeting_reports import _linkify_briefs
        meeting = ParliamentaryMeeting.objects.create(
            name="Test2", short_name="Test2",
            term=99, session=2, year=2099,
            start_date="2099-05-01", end_date="2099-06-01",
        )
        html = "<p>No dates here.</p>"
        result = _linkify_briefs(html, meeting)
        self.assertEqual(result, html)


class GenerateReportQualityLoopTests(TestCase):

    @patch("parliament.services.context_builder.build_context")
    @patch("parliament.management.commands.generate_meeting_reports._generate_illustration")
    @patch("parliament.management.commands.generate_meeting_reports.genai")
    @patch("parliament.management.commands.generate_meeting_reports.evaluate_report")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    def test_quality_log_created_on_generation(
        self, mock_eval, mock_genai, mock_illustration, mock_build_ctx
    ):
        from parliament.services.evaluator import EvaluationResult

        mock_build_ctx.return_value = {"cabinet": {}, "glossary": {}}
        mock_eval.return_value = EvaluationResult(
            verdict="PASS",
            tier1_results={"fabricated_facts": {"pass": True}},
            tier2_scores={"headline_specificity": {"score": 8}},
            tier3_flags={},
        )
        mock_illustration.return_value = None

        mock_response = MagicMock()
        mock_response.text = SAMPLE_REPORT_MD
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        meeting = _make_meeting_with_briefs()
        out = StringIO()
        call_command("generate_meeting_reports", stdout=out)

        meeting.refresh_from_db()
        self.assertNotEqual(meeting.report_html, "")
        self.assertEqual(meeting.quality_flag, "GREEN")
        self.assertEqual(QualityLog.objects.filter(content_type="report").count(), 1)

    @patch("parliament.services.context_builder.build_context")
    @patch("parliament.management.commands.generate_meeting_reports._generate_illustration")
    @patch("parliament.management.commands.generate_meeting_reports.genai")
    @patch("parliament.management.commands.generate_meeting_reports.evaluate_report")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    def test_prompt_includes_domain_context(
        self, mock_eval, mock_genai, mock_illustration, mock_build_ctx
    ):
        from parliament.services.evaluator import EvaluationResult

        mock_build_ctx.return_value = {
            "cabinet": {
                "education": {
                    "minister": "Dato' Sri Fadhlina binti Sidek",
                    "portfolio": "Minister of Education",
                }
            },
            "glossary": {"SJK(T)": "Tamil vernacular school"},
            "taxonomy": {},
        }
        mock_eval.return_value = EvaluationResult(verdict="PASS")
        mock_illustration.return_value = None

        mock_response = MagicMock()
        mock_response.text = SAMPLE_REPORT_MD
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        _make_meeting_with_briefs()
        out = StringIO()
        call_command("generate_meeting_reports", stdout=out)

        # Verify domain context was in the prompt
        call_args = mock_client.models.generate_content.call_args
        prompt_sent = call_args.kwargs.get("contents") or call_args[1].get("contents", "")
        self.assertIn("CABINET REFERENCE", prompt_sent)
        self.assertIn("Fadhlina", prompt_sent)

    @patch("parliament.services.context_builder.build_context")
    @patch("parliament.management.commands.generate_meeting_reports._generate_illustration")
    @patch("parliament.management.commands.generate_meeting_reports.genai")
    @patch("parliament.management.commands.generate_meeting_reports.evaluate_report")
    @patch("parliament.management.commands.generate_meeting_reports.correct_report")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    def test_correction_loop_on_fix_verdict(
        self, mock_correct, mock_eval, mock_genai, mock_illustration, mock_build_ctx
    ):
        from parliament.services.evaluator import EvaluationResult

        mock_build_ctx.return_value = {"cabinet": {}, "glossary": {}}
        # First eval returns FIX, second returns PASS
        mock_eval.side_effect = [
            EvaluationResult(
                verdict="FIX",
                tier2_scores={"headline_specificity": {"score": 3, "feedback": "Generic"}},
            ),
            EvaluationResult(verdict="PASS"),
        ]
        mock_correct.return_value = "## Better Headline\n\nImproved text.\n\n## Key Findings\n\n- Finding"
        mock_illustration.return_value = None

        mock_response = MagicMock()
        mock_response.text = SAMPLE_REPORT_MD
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        meeting = _make_meeting_with_briefs()
        out = StringIO()
        call_command("generate_meeting_reports", stdout=out)

        meeting.refresh_from_db()
        self.assertEqual(meeting.quality_flag, "GREEN")
        # 2 quality logs: attempt 1 (FIX) + attempt 2 (PASS)
        self.assertEqual(QualityLog.objects.filter(content_type="report").count(), 2)

    @patch("parliament.services.context_builder.build_context")
    @patch("parliament.management.commands.generate_meeting_reports._generate_illustration")
    @patch("parliament.management.commands.generate_meeting_reports.genai")
    @patch("parliament.management.commands.generate_meeting_reports.evaluate_report")
    @patch("parliament.management.commands.generate_meeting_reports.correct_report")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    def test_circuit_breaker_after_3_attempts(
        self, mock_correct, mock_eval, mock_genai, mock_illustration, mock_build_ctx
    ):
        from parliament.services.evaluator import EvaluationResult

        mock_build_ctx.return_value = {"cabinet": {}, "glossary": {}}
        # All 3 attempts return REJECT
        mock_eval.return_value = EvaluationResult(
            verdict="REJECT",
            tier1_results={"fabricated_facts": {"pass": False, "details": "Fabricated"}},
        )
        mock_correct.return_value = "## Still Bad\n\nStill failing.\n\n## Key Findings\n\n- Bad"
        mock_illustration.return_value = None

        mock_response = MagicMock()
        mock_response.text = SAMPLE_REPORT_MD
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        meeting = _make_meeting_with_briefs()
        out = StringIO()
        call_command("generate_meeting_reports", stdout=out)

        meeting.refresh_from_db()
        self.assertEqual(meeting.quality_flag, "RED")
        output = out.getvalue()
        self.assertIn("circuit breaker", output)
