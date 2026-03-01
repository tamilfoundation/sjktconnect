"""Tests for newswatch views — admin review queue."""

from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse

from newswatch.models import NewsArticle


class NewsViewsAuthTest(TestCase):
    """Verify all views require login."""

    def setUp(self):
        self.article = NewsArticle.objects.create(
            url="https://example.com/auth-test",
            title="Auth test",
            status=NewsArticle.ANALYSED,
        )

    def test_queue_requires_login(self):
        response = self.client.get(reverse("newswatch:news-queue"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_detail_requires_login(self):
        response = self.client.get(
            reverse("newswatch:news-detail", args=[self.article.pk])
        )
        self.assertEqual(response.status_code, 302)

    def test_approve_requires_login(self):
        response = self.client.post(
            reverse("newswatch:news-approve", args=[self.article.pk])
        )
        self.assertEqual(response.status_code, 302)

    def test_reject_requires_login(self):
        response = self.client.post(
            reverse("newswatch:news-reject", args=[self.article.pk])
        )
        self.assertEqual(response.status_code, 302)


class NewsQueueViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("reviewer", password="pass123")
        self.client = Client()
        self.client.login(username="reviewer", password="pass123")

        self.a1 = NewsArticle.objects.create(
            url="https://example.com/q1",
            title="Analysed article",
            status=NewsArticle.ANALYSED,
            relevance_score=4,
            sentiment="POSITIVE",
            ai_summary="Good news.",
        )
        self.a2 = NewsArticle.objects.create(
            url="https://example.com/q2",
            title="Urgent article",
            status=NewsArticle.ANALYSED,
            relevance_score=5,
            is_urgent=True,
            urgent_reason="School closure threat.",
        )
        # Not analysed — should NOT appear
        NewsArticle.objects.create(
            url="https://example.com/q3",
            title="New article",
            status=NewsArticle.NEW,
        )

    def test_queue_shows_analysed_articles(self):
        response = self.client.get(reverse("newswatch:news-queue"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Analysed article")
        self.assertContains(response, "Urgent article")
        self.assertNotContains(response, "New article")

    def test_queue_filter_by_review_status(self):
        self.a1.review_status = NewsArticle.APPROVED
        self.a1.save()

        response = self.client.get(reverse("newswatch:news-queue") + "?review=APPROVED")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Analysed article")
        self.assertNotContains(response, "Urgent article")

    def test_queue_filter_urgent(self):
        response = self.client.get(reverse("newswatch:news-queue") + "?urgent=1")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Urgent article")
        self.assertNotContains(response, "Analysed article")

    def test_queue_context_counts(self):
        response = self.client.get(reverse("newswatch:news-queue"))
        self.assertEqual(response.context["pending_count"], 2)
        self.assertEqual(response.context["urgent_count"], 1)


class NewsArticleDetailViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("reviewer", password="pass123")
        self.client = Client()
        self.client.login(username="reviewer", password="pass123")

        self.article = NewsArticle.objects.create(
            url="https://example.com/detail",
            title="Detail test article",
            body_text="The government announced funding for SJK(T) schools.",
            status=NewsArticle.ANALYSED,
            relevance_score=4,
            sentiment="POSITIVE",
            ai_summary="Funding boost for Tamil schools.",
        )

    def test_detail_renders(self):
        response = self.client.get(
            reverse("newswatch:news-detail", args=[self.article.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Detail test article")
        self.assertContains(response, "Funding boost")

    def test_detail_404_for_missing(self):
        response = self.client.get(
            reverse("newswatch:news-detail", args=[99999])
        )
        self.assertEqual(response.status_code, 404)


class ApproveRejectTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("reviewer", password="pass123")
        self.client = Client()
        self.client.login(username="reviewer", password="pass123")

        self.article = NewsArticle.objects.create(
            url="https://example.com/review-action",
            title="Review action test",
            status=NewsArticle.ANALYSED,
        )

    def test_approve_sets_status(self):
        response = self.client.post(
            reverse("newswatch:news-approve", args=[self.article.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.article.refresh_from_db()
        self.assertEqual(self.article.review_status, NewsArticle.APPROVED)
        self.assertEqual(self.article.reviewed_by, self.user)
        self.assertIsNotNone(self.article.reviewed_at)

    def test_reject_sets_status(self):
        response = self.client.post(
            reverse("newswatch:news-reject", args=[self.article.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.article.refresh_from_db()
        self.assertEqual(self.article.review_status, NewsArticle.REJECTED)

    def test_toggle_urgent_on(self):
        response = self.client.post(
            reverse("newswatch:news-toggle-urgent", args=[self.article.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.article.refresh_from_db()
        self.assertTrue(self.article.is_urgent)

    def test_toggle_urgent_off(self):
        self.article.is_urgent = True
        self.article.urgent_reason = "Crisis"
        self.article.save()

        response = self.client.post(
            reverse("newswatch:news-toggle-urgent", args=[self.article.pk])
        )
        self.article.refresh_from_db()
        self.assertFalse(self.article.is_urgent)
        self.assertEqual(self.article.urgent_reason, "")
