"""Tests for news API endpoints.

- GET /api/v1/schools/<moe_code>/news/  (school-specific news)
- GET /api/v1/news/                     (public news list)
"""

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


class PublicNewsListAPITest(TestCase):
    """Tests for GET /api/v1/news/ — public paginated news list."""

    @classmethod
    def setUpTestData(cls):
        cls.school = School.objects.create(
            moe_code="JBD0050",
            name="SJK(T) Ladang Bikam",
            short_name="SJK(T) Ladang Bikam",
            state="Johor",
        )
        cls.approved_school_article = NewsArticle.objects.create(
            url="https://example.com/school-news-1",
            title="School gets funding",
            source_name="The Star",
            published_date=datetime.datetime(2026, 3, 1, 10, 0, tzinfo=datetime.timezone.utc),
            body_text="Article about school funding.",
            status="ANALYSED",
            ai_summary="Funding approved for SJK(T) Ladang Bikam.",
            sentiment="POSITIVE",
            relevance_score=4,
            mentioned_schools=[
                {"name": "SJK(T) Ladang Bikam", "moe_code": "JBD0050"},
            ],
            review_status="APPROVED",
        )
        cls.approved_general_article = NewsArticle.objects.create(
            url="https://example.com/general-news-1",
            title="Tamil education policy update",
            source_name="Malaysiakini",
            published_date=datetime.datetime(2026, 2, 15, 8, 0, tzinfo=datetime.timezone.utc),
            body_text="General education policy article.",
            status="ANALYSED",
            ai_summary="New education policy announced.",
            sentiment="NEUTRAL",
            mentioned_schools=[],
            review_status="APPROVED",
        )
        cls.pending_article = NewsArticle.objects.create(
            url="https://example.com/pending",
            title="Pending review article",
            status="ANALYSED",
            mentioned_schools=[],
            review_status="PENDING",
        )
        cls.rejected_article = NewsArticle.objects.create(
            url="https://example.com/rejected",
            title="Rejected article",
            status="ANALYSED",
            mentioned_schools=[],
            review_status="REJECTED",
        )
        cls.non_analysed_article = NewsArticle.objects.create(
            url="https://example.com/not-analysed",
            title="Not yet analysed",
            status="EXTRACTED",
            mentioned_schools=[],
            review_status="APPROVED",
        )

    def test_returns_approved_articles(self):
        resp = self.client.get("/api/v1/news/")
        assert resp.status_code == 200
        data = resp.json()
        assert "count" in data
        assert "results" in data
        assert data["count"] == 2
        titles = [a["title"] for a in data["results"]]
        assert "School gets funding" in titles
        assert "Tamil education policy update" in titles

    def test_excludes_pending(self):
        resp = self.client.get("/api/v1/news/")
        titles = [a["title"] for a in resp.json()["results"]]
        assert "Pending review article" not in titles

    def test_excludes_rejected(self):
        resp = self.client.get("/api/v1/news/")
        titles = [a["title"] for a in resp.json()["results"]]
        assert "Rejected article" not in titles

    def test_excludes_non_analysed(self):
        resp = self.client.get("/api/v1/news/")
        titles = [a["title"] for a in resp.json()["results"]]
        assert "Not yet analysed" not in titles

    def test_search_filter_title(self):
        resp = self.client.get("/api/v1/news/?search=funding")
        data = resp.json()
        assert data["count"] == 1
        assert data["results"][0]["title"] == "School gets funding"

    def test_search_filter_ai_summary(self):
        resp = self.client.get("/api/v1/news/?search=education+policy+announced")
        data = resp.json()
        assert data["count"] == 1
        assert data["results"][0]["title"] == "Tamil education policy update"

    def test_category_school_filter(self):
        resp = self.client.get("/api/v1/news/?category=school")
        data = resp.json()
        assert data["count"] == 1
        assert data["results"][0]["title"] == "School gets funding"

    def test_category_general_filter(self):
        resp = self.client.get("/api/v1/news/?category=general")
        data = resp.json()
        assert data["count"] == 1
        assert data["results"][0]["title"] == "Tamil education policy update"

    def test_ordered_by_published_date_descending(self):
        resp = self.client.get("/api/v1/news/")
        data = resp.json()
        assert data["results"][0]["title"] == "School gets funding"
        assert data["results"][1]["title"] == "Tamil education policy update"

    def test_serializer_includes_mentioned_schools(self):
        resp = self.client.get("/api/v1/news/")
        data = resp.json()
        school_article = next(
            a for a in data["results"] if a["title"] == "School gets funding"
        )
        assert "mentioned_schools" in school_article
        assert school_article["mentioned_schools"] == [
            {"name": "SJK(T) Ladang Bikam", "moe_code": "JBD0050"},
        ]

    def test_pagination_works(self):
        resp = self.client.get("/api/v1/news/?page_size=1")
        data = resp.json()
        assert len(data["results"]) == 1
        assert data["next"] is not None
