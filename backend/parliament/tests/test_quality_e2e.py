"""End-to-end test for the full quality loop.

Verifies: generate brief -> evaluate -> log -> detect patterns.
Uses mocked Gemini calls throughout.
"""

from unittest.mock import patch

from django.test import TestCase

from hansard.models import HansardMention, HansardSitting
from parliament.models import ParliamentaryMeeting, QualityLog, SittingBrief
from parliament.services.brief_generator import generate_brief
from parliament.services.evaluator import EvaluationResult
from parliament.services.learner import detect_patterns, log_quality_summary


class BriefQualityE2ETest(TestCase):

    def setUp(self):
        self.sitting = HansardSitting.objects.create(
            sitting_date="2098-06-01",
            pdf_url="https://example.com/e2e.pdf",
            pdf_filename="e2e.pdf",
            status="COMPLETED",
        )
        HansardMention.objects.create(
            sitting=self.sitting, verbatim_quote="Budget mention",
            page_number=5,
            mp_name="YB Arul", mp_constituency="Segamat",
            mention_type="BUDGET", significance=4,
            ai_summary="MP requests RM2M for SJK(T) Ladang Bikam.",
            review_status="APPROVED",
        )

    @patch("parliament.services.brief_generator._evaluate_brief")
    def test_full_brief_cycle(self, mock_eval):
        mock_eval.return_value = EvaluationResult(
            verdict="PASS",
            tier1_results={"fabricated_facts": {"pass": True}},
            tier2_scores={"school_linkification": {"score": 9}},
            tier3_flags={"tone_drift": "OK"},
        )

        brief = generate_brief(self.sitting)

        self.assertIsNotNone(brief)
        self.assertEqual(brief.quality_flag, "GREEN")

        logs = QualityLog.objects.filter(sitting_brief=brief)
        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs.first().verdict, "PASS")


class LearnerPatternE2ETest(TestCase):

    def test_detect_patterns_with_real_logs(self):
        """Create 3 meetings with consistently low headline scores."""
        for i in range(3):
            meeting = ParliamentaryMeeting.objects.create(
                name=f"E2E Meeting {i+1}",
                short_name=f"E2E {i+1}",
                term=80+i, session=1, year=2080+i,
                start_date=f"208{i}-03-01",
                end_date=f"208{i}-03-28",
            )
            QualityLog.objects.create(
                content_type="report", meeting=meeting,
                prompt_version="v3", model_used="gemini-2.5-flash",
                attempt_number=1, verdict="PASS",
                tier1_results={},
                tier2_scores={
                    "headline_specificity": {"score": 4, "feedback": "Generic"},
                    "actionability": {"score": 8},
                    "key_findings_specificity": {"score": 7},
                },
                tier3_flags={}, quality_flag="AMBER",
            )

        flags = detect_patterns()
        self.assertTrue(len(flags) > 0)
        self.assertEqual(flags[0]["criterion"], "headline_specificity")

    def test_quality_summary_for_meeting(self):
        meeting = ParliamentaryMeeting.objects.create(
            name="E2E Summary", short_name="E2E Sum",
            term=85, session=1, year=2085,
            start_date="2085-03-01", end_date="2085-04-01",
        )
        QualityLog.objects.create(
            content_type="report", meeting=meeting,
            prompt_version="v3", model_used="gemini-2.5-flash",
            attempt_number=1, verdict="FIX",
            tier1_results={}, tier2_scores={}, tier3_flags={},
            quality_flag="AMBER",
        )
        QualityLog.objects.create(
            content_type="report", meeting=meeting,
            prompt_version="v3", model_used="gemini-2.5-flash",
            attempt_number=2, verdict="PASS",
            tier1_results={}, tier2_scores={}, tier3_flags={},
            quality_flag="GREEN",
        )

        summary = log_quality_summary(meeting)
        self.assertEqual(summary["total_attempts"], 2)
        self.assertEqual(summary["final_verdict"], "PASS")
