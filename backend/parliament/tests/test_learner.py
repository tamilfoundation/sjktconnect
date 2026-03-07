"""Tests for the learner service."""

from django.test import TestCase

from parliament.models import ParliamentaryMeeting, QualityLog
from parliament.services.learner import detect_patterns, log_quality_summary


class DetectPatternsTests(TestCase):

    def setUp(self):
        self.meetings = []
        for i in range(3):
            m = ParliamentaryMeeting.objects.create(
                name=f"Pattern Test {i+1}",
                short_name=f"Pattern {i+1}",
                term=90+i, session=1, year=2090+i,
                start_date=f"209{i}-03-01",
                end_date=f"209{i}-03-28",
            )
            self.meetings.append(m)

    def test_detects_recurring_low_score(self):
        for m in self.meetings:
            QualityLog.objects.create(
                content_type="report", meeting=m,
                prompt_version="v3", model_used="gemini-2.5-flash",
                attempt_number=1, verdict="PASS",
                tier1_results={},
                tier2_scores={
                    "headline_specificity": {"score": 4, "feedback": "Generic"},
                    "actionability": {"score": 8},
                },
                tier3_flags={}, quality_flag="AMBER",
            )

        flags = detect_patterns()
        criteria = [f["criterion"] for f in flags]
        self.assertIn("headline_specificity", criteria)

    def test_no_flags_when_scores_good(self):
        for m in self.meetings:
            QualityLog.objects.create(
                content_type="report", meeting=m,
                prompt_version="v3", model_used="gemini-2.5-flash",
                attempt_number=1, verdict="PASS",
                tier1_results={},
                tier2_scores={
                    "headline_specificity": {"score": 8},
                    "actionability": {"score": 9},
                },
                tier3_flags={}, quality_flag="GREEN",
            )

        flags = detect_patterns()
        self.assertEqual(len(flags), 0)

    def test_only_counts_final_attempt_per_meeting(self):
        """If attempt 1 scores low but attempt 2 scores high, use attempt 2."""
        for m in self.meetings:
            QualityLog.objects.create(
                content_type="report", meeting=m,
                prompt_version="v3", model_used="gemini-2.5-flash",
                attempt_number=1, verdict="FIX",
                tier1_results={},
                tier2_scores={"headline_specificity": {"score": 3}},
                tier3_flags={}, quality_flag="AMBER",
            )
            QualityLog.objects.create(
                content_type="report", meeting=m,
                prompt_version="v3", model_used="gemini-2.5-flash",
                attempt_number=2, verdict="PASS",
                tier1_results={},
                tier2_scores={"headline_specificity": {"score": 8}},
                tier3_flags={}, quality_flag="GREEN",
            )

        flags = detect_patterns()
        self.assertEqual(len(flags), 0)


class LogQualitySummaryTests(TestCase):

    def test_returns_summary_dict(self):
        meeting = ParliamentaryMeeting.objects.create(
            name="Summary Test", short_name="Summary",
            term=95, session=1, year=2095,
            start_date="2095-02-01", end_date="2095-03-01",
        )
        QualityLog.objects.create(
            content_type="report", meeting=meeting,
            prompt_version="v3", model_used="gemini-2.5-flash",
            attempt_number=1, verdict="PASS",
            tier1_results={}, tier2_scores={"headline": {"score": 8}},
            tier3_flags={}, quality_flag="GREEN",
        )

        summary = log_quality_summary(meeting)
        self.assertEqual(summary["total_attempts"], 1)
        self.assertEqual(summary["final_verdict"], "PASS")

    def test_multi_attempt_summary(self):
        meeting = ParliamentaryMeeting.objects.create(
            name="Multi Test", short_name="Multi",
            term=96, session=1, year=2096,
            start_date="2096-02-01", end_date="2096-03-01",
        )
        QualityLog.objects.create(
            content_type="report", meeting=meeting,
            prompt_version="v3", model_used="gemini-2.5-flash",
            attempt_number=1, verdict="FIX",
            tier1_results={}, tier2_scores={},
            tier3_flags={}, quality_flag="AMBER",
        )
        QualityLog.objects.create(
            content_type="report", meeting=meeting,
            prompt_version="v3", model_used="gemini-2.5-flash",
            attempt_number=2, verdict="PASS",
            tier1_results={}, tier2_scores={},
            tier3_flags={}, quality_flag="GREEN",
        )

        summary = log_quality_summary(meeting)
        self.assertEqual(summary["total_attempts"], 2)
        self.assertEqual(summary["final_verdict"], "PASS")

    def test_no_logs_returns_na(self):
        meeting = ParliamentaryMeeting.objects.create(
            name="Empty Test", short_name="Empty",
            term=97, session=1, year=2097,
            start_date="2097-02-01", end_date="2097-03-01",
        )
        summary = log_quality_summary(meeting)
        self.assertEqual(summary["total_attempts"], 0)
        self.assertEqual(summary["final_verdict"], "N/A")
