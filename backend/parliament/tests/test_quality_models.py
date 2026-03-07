"""Tests for QualityLog model and quality_flag fields."""

from django.test import TestCase

from hansard.models import HansardSitting
from parliament.models import ParliamentaryMeeting, QualityLog, SittingBrief


class QualityLogModelTests(TestCase):

    def setUp(self):
        self.meeting = ParliamentaryMeeting.objects.create(
            name="Quality Test Meeting",
            short_name="QT Meeting",
            term=99, session=1, year=2099,
            start_date="2099-02-24", end_date="2099-04-10",
        )

    def test_create_report_quality_log(self):
        log = QualityLog.objects.create(
            content_type="report",
            meeting=self.meeting,
            prompt_version="v3",
            model_used="gemini-2.5-flash",
            attempt_number=1,
            verdict="PASS",
            tier1_results={"fabricated_facts": {"pass": True}},
            tier2_scores={"headline_specificity": {"score": 8}},
            tier3_flags={"illustration_similarity": "OK"},
            corrections_applied=[],
            quality_flag="GREEN",
        )
        self.assertEqual(log.content_type, "report")
        self.assertEqual(log.verdict, "PASS")
        self.assertEqual(log.quality_flag, "GREEN")

    def test_create_brief_quality_log(self):
        sitting = HansardSitting.objects.create(
            sitting_date="2025-02-24",
            pdf_url="https://example.com/test.pdf",
            pdf_filename="test.pdf",
        )
        brief = SittingBrief.objects.create(
            sitting=sitting,
            title="Test",
            summary_html="<p>Test</p>",
        )
        log = QualityLog.objects.create(
            content_type="brief",
            sitting_brief=brief,
            prompt_version="v1",
            model_used="gemini-2.5-flash",
            attempt_number=2,
            verdict="FIX",
            tier1_results={},
            tier2_scores={"school_linkification": {"score": 4}},
            tier3_flags={},
            corrections_applied=[{"type": "re-prompt", "target": "jargon"}],
            quality_flag="AMBER",
        )
        self.assertEqual(log.sitting_brief, brief)
        self.assertEqual(log.attempt_number, 2)

    def test_quality_log_str(self):
        log = QualityLog.objects.create(
            content_type="report",
            meeting=self.meeting,
            prompt_version="v3",
            model_used="gemini-2.5-flash",
            attempt_number=1,
            verdict="PASS",
            tier1_results={},
            tier2_scores={},
            tier3_flags={},
            quality_flag="GREEN",
        )
        self.assertIn("report", str(log))
        self.assertIn("PASS", str(log))


class QualityFlagFieldTests(TestCase):

    def test_meeting_quality_flag_default(self):
        meeting = ParliamentaryMeeting.objects.create(
            name="Test Meeting", short_name="Test",
            term=99, session=2, year=2099,
            start_date="2099-06-01", end_date="2099-07-01",
        )
        self.assertEqual(meeting.quality_flag, "")

    def test_brief_quality_flag_default(self):
        sitting = HansardSitting.objects.create(
            sitting_date="2025-06-01",
            pdf_url="https://example.com/test.pdf",
            pdf_filename="test.pdf",
        )
        brief = SittingBrief.objects.create(
            sitting=sitting,
            title="Test",
            summary_html="<p>Test</p>",
        )
        self.assertEqual(brief.quality_flag, "")

    def test_meeting_quality_flag_set(self):
        meeting = ParliamentaryMeeting.objects.create(
            name="Test Meeting 2", short_name="Test 2",
            term=99, session=3, year=2099,
            start_date="2099-10-01", end_date="2099-12-01",
        )
        meeting.quality_flag = "GREEN"
        meeting.save(update_fields=["quality_flag"])
        meeting.refresh_from_db()
        self.assertEqual(meeting.quality_flag, "GREEN")
