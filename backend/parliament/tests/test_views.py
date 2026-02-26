"""Tests for Sprint 0.5 — admin review queue and public parliament watch views."""

from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from core.models import AuditLog
from hansard.models import HansardMention, HansardSitting
from parliament.models import SittingBrief


def _create_sitting(sitting_date="2026-01-26"):
    return HansardSitting.objects.create(
        sitting_date=sitting_date,
        pdf_url="https://example.com/test.pdf",
        pdf_filename="test.pdf",
        status="COMPLETED",
    )


def _create_mention(sitting, page=1, status="PENDING", **kwargs):
    defaults = {
        "verbatim_quote": f"SJK(T) Ladang Bikam on page {page}",
        "page_number": page,
        "keyword_matched": "SJK(T)",
        "mp_name": "YB Arul",
        "mp_constituency": "Segamat",
        "mp_party": "BN",
        "mention_type": "QUESTION",
        "significance": 4,
        "sentiment": "ADVOCATING",
        "change_indicator": "NEW",
        "ai_summary": "MP asked about school funding.",
        "review_status": status,
    }
    defaults.update(kwargs)
    return HansardMention.objects.create(sitting=sitting, **defaults)


# --- Authentication tests ---


class LoginRequiredTests(TestCase):
    """Admin views redirect anonymous users to login."""

    def setUp(self):
        self.client = Client()
        self.sitting = _create_sitting()
        self.mention = _create_mention(self.sitting)

    def test_review_queue_requires_login(self):
        resp = self.client.get(reverse("parliament:review-queue"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp.url)

    def test_sitting_review_requires_login(self):
        resp = self.client.get(
            reverse("parliament:sitting-review", kwargs={"sitting_pk": self.sitting.pk})
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp.url)

    def test_mention_detail_requires_login(self):
        resp = self.client.get(
            reverse("parliament:mention-detail", kwargs={"pk": self.mention.pk})
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp.url)

    def test_approve_requires_login(self):
        resp = self.client.post(
            reverse("parliament:mention-approve", kwargs={"pk": self.mention.pk})
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp.url)

    def test_reject_requires_login(self):
        resp = self.client.post(
            reverse("parliament:mention-reject", kwargs={"pk": self.mention.pk})
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp.url)

    def test_publish_requires_login(self):
        resp = self.client.post(
            reverse("parliament:publish-brief", kwargs={"sitting_pk": self.sitting.pk})
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp.url)


class PublicViewAccessTests(TestCase):
    """Public views are accessible without login."""

    def test_parliament_watch_accessible(self):
        resp = self.client.get(reverse("parliament:watch"))
        self.assertEqual(resp.status_code, 200)

    def test_brief_detail_404_when_not_published(self):
        sitting = _create_sitting()
        SittingBrief.objects.create(
            sitting=sitting,
            title="Test Brief",
            summary_html="<p>Summary</p>",
            is_published=False,
        )
        resp = self.client.get(
            reverse("parliament:brief-detail", kwargs={"sitting_date": "2026-01-26"})
        )
        self.assertEqual(resp.status_code, 404)


# --- Review queue ---


class ReviewQueueViewTests(TestCase):
    """Tests for the sitting-level review queue."""

    def setUp(self):
        self.user = User.objects.create_user("admin", password="testpass")
        self.client = Client()
        self.client.login(username="admin", password="testpass")

    def test_empty_queue(self):
        resp = self.client.get(reverse("parliament:review-queue"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["sittings"]), 0)

    def test_sittings_with_mentions_appear(self):
        sitting = _create_sitting()
        _create_mention(sitting)
        resp = self.client.get(reverse("parliament:review-queue"))
        self.assertEqual(len(resp.context["sittings"]), 1)

    def test_sitting_without_mentions_excluded(self):
        _create_sitting()  # No mentions
        resp = self.client.get(reverse("parliament:review-queue"))
        self.assertEqual(len(resp.context["sittings"]), 0)

    def test_counts_annotated(self):
        sitting = _create_sitting()
        _create_mention(sitting, page=1, status="PENDING")
        _create_mention(sitting, page=2, status="APPROVED")
        _create_mention(sitting, page=3, status="REJECTED")

        resp = self.client.get(reverse("parliament:review-queue"))
        s = resp.context["sittings"][0]
        self.assertEqual(s.pending_count, 1)
        self.assertEqual(s.approved_count, 1)
        self.assertEqual(s.rejected_count, 1)
        self.assertEqual(s.total_mention_count, 3)

    def test_ordered_by_date_desc(self):
        s1 = _create_sitting("2026-01-10")
        _create_mention(s1)
        s2 = _create_sitting("2026-02-15")
        _create_mention(s2)

        resp = self.client.get(reverse("parliament:review-queue"))
        sittings = list(resp.context["sittings"])
        self.assertEqual(sittings[0].sitting_date, date(2026, 2, 15))
        self.assertEqual(sittings[1].sitting_date, date(2026, 1, 10))


# --- Sitting review ---


class SittingReviewViewTests(TestCase):
    """Tests for the per-sitting mention list."""

    def setUp(self):
        self.user = User.objects.create_user("admin", password="testpass")
        self.client = Client()
        self.client.login(username="admin", password="testpass")

    def test_lists_mentions_for_sitting(self):
        sitting = _create_sitting()
        _create_mention(sitting, page=1)
        _create_mention(sitting, page=5)

        resp = self.client.get(
            reverse("parliament:sitting-review", kwargs={"sitting_pk": sitting.pk})
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["mentions"]), 2)
        self.assertEqual(resp.context["sitting"], sitting)

    def test_404_for_invalid_sitting(self):
        resp = self.client.get(
            reverse("parliament:sitting-review", kwargs={"sitting_pk": 99999})
        )
        self.assertEqual(resp.status_code, 404)


# --- Mention detail ---


class MentionDetailViewTests(TestCase):
    """Tests for the split-screen mention review."""

    def setUp(self):
        self.user = User.objects.create_user("admin", password="testpass")
        self.client = Client()
        self.client.login(username="admin", password="testpass")

    def test_detail_includes_form(self):
        sitting = _create_sitting()
        mention = _create_mention(sitting)

        resp = self.client.get(
            reverse("parliament:mention-detail", kwargs={"pk": mention.pk})
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("form", resp.context)
        self.assertEqual(resp.context["mention"], mention)

    def test_detail_includes_siblings(self):
        sitting = _create_sitting()
        _create_mention(sitting, page=1)
        _create_mention(sitting, page=5)

        m = sitting.mentions.first()
        resp = self.client.get(
            reverse("parliament:mention-detail", kwargs={"pk": m.pk})
        )
        self.assertEqual(len(resp.context["siblings"]), 2)


# --- Approve ---


class ApproveMentionViewTests(TestCase):
    """Tests for approving a mention (optionally with edits)."""

    def setUp(self):
        self.user = User.objects.create_user("admin", password="testpass")
        self.client = Client()
        self.client.login(username="admin", password="testpass")
        self.sitting = _create_sitting()
        self.mention = _create_mention(self.sitting)

    def test_approve_sets_status(self):
        resp = self.client.post(
            reverse("parliament:mention-approve", kwargs={"pk": self.mention.pk}),
            data={
                "mp_name": "YB Arul",
                "mp_constituency": "Segamat",
                "mp_party": "BN",
                "mention_type": "QUESTION",
                "significance": 4,
                "sentiment": "ADVOCATING",
                "change_indicator": "NEW",
                "ai_summary": "MP asked about school funding.",
                "review_notes": "",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.mention.refresh_from_db()
        self.assertEqual(self.mention.review_status, "APPROVED")
        self.assertEqual(self.mention.reviewed_by, "admin")
        self.assertIsNotNone(self.mention.reviewed_at)

    def test_approve_redirects_to_sitting_review(self):
        resp = self.client.post(
            reverse("parliament:mention-approve", kwargs={"pk": self.mention.pk}),
            data={
                "mp_name": "YB Arul",
                "mp_constituency": "Segamat",
                "mp_party": "BN",
                "ai_summary": "Summary.",
                "review_notes": "",
            },
        )
        self.assertRedirects(
            resp,
            reverse("parliament:sitting-review", kwargs={"sitting_pk": self.sitting.pk}),
            fetch_redirect_response=False,
        )

    def test_approve_with_edits(self):
        """Reviewer can change AI analysis fields when approving."""
        self.client.post(
            reverse("parliament:mention-approve", kwargs={"pk": self.mention.pk}),
            data={
                "mp_name": "YB Arulkumar",  # Corrected name
                "mp_constituency": "Segamat",
                "mp_party": "BN",
                "mention_type": "BUDGET",  # Changed type
                "significance": 5,  # Changed significance
                "sentiment": "PROMISING",
                "change_indicator": "NEW",
                "ai_summary": "Corrected summary by reviewer.",
                "review_notes": "Name and type corrected.",
            },
        )
        self.mention.refresh_from_db()
        self.assertEqual(self.mention.mp_name, "YB Arulkumar")
        self.assertEqual(self.mention.mention_type, "BUDGET")
        self.assertEqual(self.mention.significance, 5)
        self.assertEqual(self.mention.ai_summary, "Corrected summary by reviewer.")
        self.assertEqual(self.mention.review_notes, "Name and type corrected.")

    def test_approve_creates_audit_log(self):
        """AuditLog should record the mention update."""
        initial_count = AuditLog.objects.filter(
            target_type="HansardMention", action="update"
        ).count()

        self.client.post(
            reverse("parliament:mention-approve", kwargs={"pk": self.mention.pk}),
            data={
                "mp_name": "YB Arul",
                "mp_constituency": "Segamat",
                "mp_party": "BN",
                "ai_summary": "Summary.",
                "review_notes": "",
            },
        )

        new_count = AuditLog.objects.filter(
            target_type="HansardMention", action="update"
        ).count()
        self.assertGreater(new_count, initial_count)


# --- Reject ---


class RejectMentionViewTests(TestCase):
    """Tests for rejecting a mention."""

    def setUp(self):
        self.user = User.objects.create_user("admin", password="testpass")
        self.client = Client()
        self.client.login(username="admin", password="testpass")
        self.sitting = _create_sitting()
        self.mention = _create_mention(self.sitting)

    def test_reject_sets_status(self):
        resp = self.client.post(
            reverse("parliament:mention-reject", kwargs={"pk": self.mention.pk}),
            data={"review_notes": "Not relevant."},
        )
        self.assertEqual(resp.status_code, 302)
        self.mention.refresh_from_db()
        self.assertEqual(self.mention.review_status, "REJECTED")
        self.assertEqual(self.mention.reviewed_by, "admin")
        self.assertEqual(self.mention.review_notes, "Not relevant.")

    def test_reject_redirects_to_sitting_review(self):
        resp = self.client.post(
            reverse("parliament:mention-reject", kwargs={"pk": self.mention.pk}),
            data={"review_notes": ""},
        )
        self.assertRedirects(
            resp,
            reverse("parliament:sitting-review", kwargs={"sitting_pk": self.sitting.pk}),
            fetch_redirect_response=False,
        )

    def test_reject_creates_audit_log(self):
        initial_count = AuditLog.objects.filter(
            target_type="HansardMention", action="update"
        ).count()

        self.client.post(
            reverse("parliament:mention-reject", kwargs={"pk": self.mention.pk}),
            data={"review_notes": "Irrelevant."},
        )

        new_count = AuditLog.objects.filter(
            target_type="HansardMention", action="update"
        ).count()
        self.assertGreater(new_count, initial_count)


# --- Publish brief ---


class PublishBriefViewTests(TestCase):
    """Tests for generating and publishing a SittingBrief."""

    def setUp(self):
        self.user = User.objects.create_user("admin", password="testpass")
        self.client = Client()
        self.client.login(username="admin", password="testpass")
        self.sitting = _create_sitting()
        _create_mention(self.sitting, status="APPROVED")

    @patch("parliament.views.generate_brief")
    def test_publish_creates_brief(self, mock_generate):
        brief = SittingBrief.objects.create(
            sitting=self.sitting,
            title="Test Brief",
            summary_html="<p>Summary</p>",
            social_post_text="Social post",
        )
        mock_generate.return_value = brief

        resp = self.client.post(
            reverse("parliament:publish-brief", kwargs={"sitting_pk": self.sitting.pk})
        )
        self.assertEqual(resp.status_code, 302)
        brief.refresh_from_db()
        self.assertTrue(brief.is_published)
        self.assertIsNotNone(brief.published_at)

    @patch("parliament.views.generate_brief")
    def test_publish_redirects_to_sitting_review(self, mock_generate):
        brief = SittingBrief.objects.create(
            sitting=self.sitting,
            title="Test Brief",
            summary_html="<p>Summary</p>",
        )
        mock_generate.return_value = brief

        resp = self.client.post(
            reverse("parliament:publish-brief", kwargs={"sitting_pk": self.sitting.pk})
        )
        self.assertRedirects(
            resp,
            reverse("parliament:sitting-review", kwargs={"sitting_pk": self.sitting.pk}),
            fetch_redirect_response=False,
        )

    @patch("parliament.views.generate_brief")
    def test_publish_handles_none_brief(self, mock_generate):
        """If brief generation fails, should still redirect without error."""
        mock_generate.return_value = None

        resp = self.client.post(
            reverse("parliament:publish-brief", kwargs={"sitting_pk": self.sitting.pk})
        )
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(SittingBrief.objects.filter(sitting=self.sitting).exists())


# --- Public parliament watch ---


class ParliamentWatchViewTests(TestCase):
    """Tests for the public parliament watch page."""

    def test_empty_when_no_published_briefs(self):
        resp = self.client.get(reverse("parliament:watch"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["briefs"]), 0)

    def test_shows_published_briefs(self):
        sitting = _create_sitting()
        SittingBrief.objects.create(
            sitting=sitting,
            title="Published Brief",
            summary_html="<p>Summary</p>",
            is_published=True,
        )
        resp = self.client.get(reverse("parliament:watch"))
        self.assertEqual(len(resp.context["briefs"]), 1)

    def test_excludes_unpublished_briefs(self):
        sitting = _create_sitting()
        SittingBrief.objects.create(
            sitting=sitting,
            title="Draft Brief",
            summary_html="<p>Summary</p>",
            is_published=False,
        )
        resp = self.client.get(reverse("parliament:watch"))
        self.assertEqual(len(resp.context["briefs"]), 0)


class BriefDetailViewTests(TestCase):
    """Tests for the public brief detail page."""

    def test_published_brief_accessible(self):
        sitting = _create_sitting("2026-02-10")
        SittingBrief.objects.create(
            sitting=sitting,
            title="Test Brief",
            summary_html="<p>Content</p>",
            social_post_text="Social text",
            is_published=True,
        )
        resp = self.client.get(
            reverse("parliament:brief-detail", kwargs={"sitting_date": "2026-02-10"})
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["brief"].sitting, sitting)

    def test_unpublished_brief_returns_404(self):
        sitting = _create_sitting("2026-02-10")
        SittingBrief.objects.create(
            sitting=sitting,
            title="Draft",
            summary_html="<p>Content</p>",
            is_published=False,
        )
        resp = self.client.get(
            reverse("parliament:brief-detail", kwargs={"sitting_date": "2026-02-10"})
        )
        self.assertEqual(resp.status_code, 404)

    def test_nonexistent_date_returns_404(self):
        resp = self.client.get(
            reverse("parliament:brief-detail", kwargs={"sitting_date": "2099-12-31"})
        )
        self.assertEqual(resp.status_code, 404)
