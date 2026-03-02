"""Tests for GET /api/v1/schools/<moe_code>/news/ endpoint."""

import datetime

from django.test import TestCase

from newswatch.models import NewsArticle
from schools.models import School


class SchoolNewsAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.school = School.objects.create(
            moe_code="JBD0050",
            name="SJK(T) Ladang Bikam",
            short_name="SJK(T) Ladang Bikam",
            state="Johor",
        )
        cls.approved_article = NewsArticle.objects.create(
            url="https://example.com/article-1",
            title="Tamil school gets new building",
            source_name="The Star",
            published_date=datetime.datetime(2026, 3, 1, 10, 0, tzinfo=datetime.timezone.utc),
            body_text="Article body text about the school.",
            status="ANALYSED",
            ai_summary="New building for SJK(T) Ladang Bikam.",
            sentiment="POSITIVE",
            relevance_score=4,
            mentioned_schools=[
                {"name": "SJK(T) Ladang Bikam", "moe_code": "JBD0050"},
            ],
            review_status="APPROVED",
        )

    def test_returns_approved_articles(self):
        resp = self.client.get("/api/v1/schools/JBD0050/news/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        article = data[0]
        assert article["title"] == "Tamil school gets new building"
        assert article["source_name"] == "The Star"
        assert article["ai_summary"] == "New building for SJK(T) Ladang Bikam."
        assert article["sentiment"] == "POSITIVE"
        assert article["is_urgent"] is False
        assert article["url"] == "https://example.com/article-1"

    def test_excludes_pending_articles(self):
        NewsArticle.objects.create(
            url="https://example.com/pending",
            title="Pending article",
            status="ANALYSED",
            mentioned_schools=[{"name": "Test", "moe_code": "JBD0050"}],
            review_status="PENDING",
        )
        resp = self.client.get("/api/v1/schools/JBD0050/news/")
        titles = [a["title"] for a in resp.json()]
        assert "Pending article" not in titles

    def test_excludes_rejected_articles(self):
        NewsArticle.objects.create(
            url="https://example.com/rejected",
            title="Rejected article",
            status="ANALYSED",
            mentioned_schools=[{"name": "Test", "moe_code": "JBD0050"}],
            review_status="REJECTED",
        )
        resp = self.client.get("/api/v1/schools/JBD0050/news/")
        titles = [a["title"] for a in resp.json()]
        assert "Rejected article" not in titles

    def test_excludes_articles_for_other_schools(self):
        School.objects.create(
            moe_code="JBD9999",
            name="SJK(T) Other",
            short_name="SJK(T) Other",
            state="Johor",
        )
        NewsArticle.objects.create(
            url="https://example.com/other-school",
            title="Other school article",
            status="ANALYSED",
            mentioned_schools=[{"name": "Other", "moe_code": "JBD9999"}],
            review_status="APPROVED",
        )
        resp = self.client.get("/api/v1/schools/JBD0050/news/")
        titles = [a["title"] for a in resp.json()]
        assert "Other school article" not in titles

    def test_returns_empty_for_school_with_no_articles(self):
        School.objects.create(
            moe_code="JBD8888",
            name="SJK(T) No News",
            short_name="SJK(T) No News",
            state="Johor",
        )
        resp = self.client.get("/api/v1/schools/JBD8888/news/")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_ordered_by_published_date_descending(self):
        NewsArticle.objects.create(
            url="https://example.com/older",
            title="Older article",
            published_date=datetime.datetime(2026, 2, 1, 10, 0, tzinfo=datetime.timezone.utc),
            status="ANALYSED",
            mentioned_schools=[{"name": "Test", "moe_code": "JBD0050"}],
            review_status="APPROVED",
        )
        resp = self.client.get("/api/v1/schools/JBD0050/news/")
        data = resp.json()
        assert len(data) == 2
        assert data[0]["title"] == "Tamil school gets new building"
        assert data[1]["title"] == "Older article"

    def test_article_with_multiple_schools_appears_for_each(self):
        School.objects.create(
            moe_code="JBD7777",
            name="SJK(T) Second",
            short_name="SJK(T) Second",
            state="Johor",
        )
        NewsArticle.objects.create(
            url="https://example.com/multi-school",
            title="Two schools mentioned",
            status="ANALYSED",
            mentioned_schools=[
                {"name": "SJK(T) Ladang Bikam", "moe_code": "JBD0050"},
                {"name": "SJK(T) Second", "moe_code": "JBD7777"},
            ],
            review_status="APPROVED",
        )
        resp1 = self.client.get("/api/v1/schools/JBD0050/news/")
        resp2 = self.client.get("/api/v1/schools/JBD7777/news/")
        assert any(a["title"] == "Two schools mentioned" for a in resp1.json())
        assert any(a["title"] == "Two schools mentioned" for a in resp2.json())
