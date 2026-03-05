"""Tests for brief generator service."""

from django.test import TestCase

from hansard.models import HansardMention, HansardSitting
from parliament.models import SittingBrief
from parliament.services.brief_generator import (
    _build_social_post,
    _build_title,
    generate_all_pending_briefs,
    generate_brief,
)


class GenerateBriefTests(TestCase):
    """Test brief generation from approved mentions."""

    def setUp(self):
        self.sitting = HansardSitting.objects.create(
            sitting_date="2026-01-26",
            pdf_url="https://example.com/test.pdf",
            pdf_filename="test.pdf",
        )

        # 3 approved, analysed mentions
        HansardMention.objects.create(
            sitting=self.sitting, verbatim_quote="Q1", page_number=5,
            mp_name="YB Arul", mp_constituency="Segamat", mp_party="BN",
            mention_type="BUDGET", significance=4, sentiment="ADVOCATING",
            change_indicator="NEW",
            ai_summary="MP requests RM2 million for SJK(T) Ladang Bikam.",
            review_status="APPROVED",
        )
        HansardMention.objects.create(
            sitting=self.sitting, verbatim_quote="Q2", page_number=10,
            mp_name="YB Kumar", mp_constituency="Tapah", mp_party="PH",
            mention_type="QUESTION", significance=3, sentiment="NEUTRAL",
            change_indicator="NEW",
            ai_summary="MP asks about teacher shortages in Tamil schools.",
            review_status="APPROVED",
        )
        HansardMention.objects.create(
            sitting=self.sitting, verbatim_quote="Q3", page_number=20,
            mp_name="YB Siva", mp_constituency="Klang", mp_party="DAP",
            mention_type="POLICY", significance=5, sentiment="CRITICAL",
            change_indicator="ESCALATION",
            ai_summary="MP criticises delays in Tamil school repairs.",
            review_status="APPROVED",
        )

    def test_brief_created(self):
        brief = generate_brief(self.sitting)
        self.assertIsNotNone(brief)
        self.assertIsInstance(brief, SittingBrief)
        self.assertEqual(brief.sitting, self.sitting)

    def test_title_includes_count(self):
        brief = generate_brief(self.sitting)
        self.assertIn("3", brief.title)
        self.assertIn("Tamil School", brief.title)

    def test_html_contains_all_summaries(self):
        brief = generate_brief(self.sitting)
        self.assertIn("RM2 million", brief.summary_html)
        self.assertIn("teacher shortages", brief.summary_html)
        self.assertIn("Tamil school repairs", brief.summary_html)

    def test_html_contains_mp_names(self):
        brief = generate_brief(self.sitting)
        self.assertIn("YB Arul", brief.summary_html)
        self.assertIn("YB Kumar", brief.summary_html)
        self.assertIn("YB Siva", brief.summary_html)

    def test_social_post_under_280_chars(self):
        brief = generate_brief(self.sitting)
        self.assertLessEqual(len(brief.social_post_text), 280)

    def test_social_post_includes_count(self):
        brief = generate_brief(self.sitting)
        self.assertIn("3", brief.social_post_text)

    def test_brief_not_published_by_default(self):
        brief = generate_brief(self.sitting)
        self.assertFalse(brief.is_published)
        self.assertIsNone(brief.published_at)

    def test_idempotent_update(self):
        brief1 = generate_brief(self.sitting)
        brief2 = generate_brief(self.sitting)
        self.assertEqual(brief1.pk, brief2.pk)
        self.assertEqual(SittingBrief.objects.count(), 1)

    def test_no_mentions_returns_none(self):
        empty_sitting = HansardSitting.objects.create(
            sitting_date="2026-02-01",
            pdf_url="https://example.com/empty.pdf",
            pdf_filename="empty.pdf",
        )
        brief = generate_brief(empty_sitting)
        self.assertIsNone(brief)

    def test_falls_back_to_all_analysed_if_none_approved(self):
        """If no mentions are APPROVED, use all analysed mentions."""
        sitting2 = HansardSitting.objects.create(
            sitting_date="2026-03-01",
            pdf_url="https://example.com/test2.pdf",
            pdf_filename="test2.pdf",
        )
        HansardMention.objects.create(
            sitting=sitting2, verbatim_quote="Unapproved mention",
            page_number=1,
            mp_name="YB Test", mp_constituency="Test",
            mention_type="OTHER", significance=2,
            ai_summary="Fallback test.",
            review_status="PENDING",
        )
        brief = generate_brief(sitting2)
        self.assertIsNotNone(brief)
        self.assertIn("Fallback test", brief.summary_html)


class BuildTitleTests(TestCase):
    """Test title construction."""

    def setUp(self):
        self.sitting = HansardSitting.objects.create(
            sitting_date="2026-01-26",
            pdf_url="https://example.com/test.pdf",
            pdf_filename="test.pdf",
        )

    def test_singular_mention(self):
        HansardMention.objects.create(
            sitting=self.sitting, verbatim_quote="Q1",
            mp_name="YB Test", review_status="APPROVED",
        )
        mentions = self.sitting.mentions.exclude(mp_name="")
        title = _build_title(self.sitting, mentions)
        self.assertIn("Mention", title)
        self.assertNotIn("Mentions", title)

    def test_plural_mentions(self):
        for i in range(3):
            HansardMention.objects.create(
                sitting=self.sitting, verbatim_quote=f"Q{i}",
                mp_name="YB Test", review_status="APPROVED",
            )
        mentions = self.sitting.mentions.exclude(mp_name="")
        title = _build_title(self.sitting, mentions)
        self.assertIn("3", title)
        self.assertIn("Mentions", title)


class BuildSocialPostTests(TestCase):
    """Test social post construction."""

    def setUp(self):
        self.sitting = HansardSitting.objects.create(
            sitting_date="2026-01-26",
            pdf_url="https://example.com/test.pdf",
            pdf_filename="test.pdf",
        )

    def test_always_under_280(self):
        for i in range(5):
            HansardMention.objects.create(
                sitting=self.sitting, verbatim_quote=f"Q{i}",
                mp_name=f"YB Very Long Name Person {i}",
                ai_summary="A" * 200,
                significance=i + 1,
                review_status="APPROVED",
            )
        mentions = self.sitting.mentions.exclude(mp_name="")
        post = _build_social_post(self.sitting, mentions)
        self.assertLessEqual(len(post), 280)


class GenerateAllPendingBriefsTests(TestCase):
    """Tests for generate_all_pending_briefs."""

    def test_generates_only_for_missing_briefs(self):
        """sitting1 has mentions + no brief → generated;
        sitting2 has mentions + existing brief → skipped."""
        sitting1 = HansardSitting.objects.create(
            sitting_date="2026-04-01",
            pdf_url="https://example.com/s1.pdf",
            pdf_filename="s1.pdf",
            status="COMPLETED",
        )
        HansardMention.objects.create(
            sitting=sitting1, verbatim_quote="Q1", page_number=1,
            mp_name="YB Arul", ai_summary="Budget request for Tamil school.",
            review_status="APPROVED",
        )

        sitting2 = HansardSitting.objects.create(
            sitting_date="2026-04-02",
            pdf_url="https://example.com/s2.pdf",
            pdf_filename="s2.pdf",
            status="COMPLETED",
        )
        HansardMention.objects.create(
            sitting=sitting2, verbatim_quote="Q2", page_number=2,
            mp_name="YB Kumar", ai_summary="Teacher shortage query.",
            review_status="APPROVED",
        )
        # Pre-create a brief for sitting2
        SittingBrief.objects.create(
            sitting=sitting2,
            title="Existing brief",
            summary_html="<p>Already exists</p>",
            social_post_text="Already exists",
        )

        result = generate_all_pending_briefs()

        self.assertEqual(result["generated"], 1)
        # sitting1 now has a brief
        self.assertTrue(SittingBrief.objects.filter(sitting=sitting1).exists())
        # sitting2 brief unchanged
        self.assertEqual(
            SittingBrief.objects.get(sitting=sitting2).title,
            "Existing brief",
        )

    def test_skips_sittings_without_analysed_mentions(self):
        """Sitting with mentions that have empty ai_summary → skipped."""
        sitting = HansardSitting.objects.create(
            sitting_date="2026-04-03",
            pdf_url="https://example.com/s3.pdf",
            pdf_filename="s3.pdf",
            status="COMPLETED",
        )
        HansardMention.objects.create(
            sitting=sitting, verbatim_quote="Q1", page_number=1,
            mp_name="YB Test", ai_summary="",
            review_status="APPROVED",
        )

        result = generate_all_pending_briefs()

        self.assertEqual(result["generated"], 0)
        self.assertFalse(SittingBrief.objects.filter(sitting=sitting).exists())
