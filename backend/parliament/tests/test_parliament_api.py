"""Tests for MPScorecard and SittingBrief REST API endpoints."""

import datetime

from django.test import TestCase
from django.utils import timezone

from hansard.models import HansardSitting
from parliament.models import MPScorecard, SittingBrief
from schools.models import Constituency


class MPScorecardAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.constituency = Constituency.objects.create(
            code="P140", name="Segamat", state="Johor",
        )
        cls.scorecard = MPScorecard.objects.create(
            mp_name="Yuneswaran",
            constituency=cls.constituency,
            party="PH (PKR)",
            coalition="PH",
            total_mentions=5,
            substantive_mentions=3,
            questions_asked=2,
            commitments_made=1,
            last_mention_date=datetime.date(2026, 2, 26),
            school_count=4,
            total_enrolment=500,
        )

    def test_scorecard_list(self):
        resp = self.client.get("/api/v1/scorecards/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        result = data["results"][0]
        assert result["mp_name"] == "Yuneswaran"
        assert result["constituency_code"] == "P140"
        assert result["total_mentions"] == 5

    def test_scorecard_list_filter_constituency(self):
        resp = self.client.get("/api/v1/scorecards/?constituency=P140")
        assert resp.json()["count"] == 1

    def test_scorecard_list_filter_party(self):
        resp = self.client.get("/api/v1/scorecards/?party=PKR")
        assert resp.json()["count"] == 1

    def test_scorecard_list_filter_party_no_match(self):
        resp = self.client.get("/api/v1/scorecards/?party=BN")
        assert resp.json()["count"] == 0

    def test_scorecard_detail(self):
        resp = self.client.get(f"/api/v1/scorecards/{self.scorecard.pk}/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["mp_name"] == "Yuneswaran"
        assert data["substantive_mentions"] == 3

    def test_scorecard_detail_not_found(self):
        resp = self.client.get("/api/v1/scorecards/99999/")
        assert resp.status_code == 404


class SittingBriefAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.sitting = HansardSitting.objects.create(
            sitting_date=datetime.date(2026, 2, 26),
            pdf_url="https://example.com/DR-26022026.pdf",
            pdf_filename="DR-26022026.pdf",
            status="COMPLETED",
            mention_count=3,
        )
        cls.published_brief = SittingBrief.objects.create(
            sitting=cls.sitting,
            title="Tamil schools discussed on 26 Feb 2026",
            summary_html="<p>Summary</p>",
            social_post_text="3 mentions today",
            is_published=True,
            published_at=timezone.now(),
        )
        # Unpublished brief with content — should appear (content gate, not publish gate)
        sitting2 = HansardSitting.objects.create(
            sitting_date=datetime.date(2026, 2, 25),
            pdf_url="https://example.com/DR-25022026.pdf",
            pdf_filename="DR-25022026.pdf",
            status="COMPLETED",
            mention_count=1,
        )
        SittingBrief.objects.create(
            sitting=sitting2,
            title="Draft brief",
            summary_html="<p>Draft</p>",
            is_published=False,
        )
        # Empty brief — should NOT appear
        sitting3 = HansardSitting.objects.create(
            sitting_date=datetime.date(2026, 2, 24),
            pdf_url="https://example.com/DR-24022026.pdf",
            pdf_filename="DR-24022026.pdf",
            status="COMPLETED",
            mention_count=0,
        )
        SittingBrief.objects.create(
            sitting=sitting3,
            title="Empty brief",
            summary_html="",
            is_published=False,
        )

    def test_brief_list_shows_all_with_content(self):
        resp = self.client.get("/api/v1/briefs/")
        assert resp.status_code == 200
        data = resp.json()
        # 2 briefs have content (published + draft), 1 empty excluded
        assert data["count"] == 2

    def test_brief_list_has_sitting_date(self):
        resp = self.client.get("/api/v1/briefs/")
        result = resp.json()["results"][0]
        assert result["sitting_date"] == "2026-02-26"
        assert result["mention_count"] == 3

    def test_brief_detail(self):
        resp = self.client.get(f"/api/v1/briefs/{self.published_brief.pk}/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Tamil schools discussed on 26 Feb 2026"
        assert "<p>Summary</p>" in data["summary_html"]

    def test_brief_detail_empty_returns_404(self):
        empty = SittingBrief.objects.get(summary_html="")
        resp = self.client.get(f"/api/v1/briefs/{empty.pk}/")
        assert resp.status_code == 404

    def test_brief_detail_not_found(self):
        resp = self.client.get("/api/v1/briefs/99999/")
        assert resp.status_code == 404
