"""Tests for the MentionReviewForm."""

from django.test import TestCase

from hansard.models import HansardMention, HansardSitting
from parliament.forms import MentionReviewForm


class MentionReviewFormTests(TestCase):
    """Test the review form validates and saves correctly."""

    def setUp(self):
        self.sitting = HansardSitting.objects.create(
            sitting_date="2026-01-26",
            pdf_url="https://example.com/test.pdf",
            pdf_filename="test.pdf",
        )
        self.mention = HansardMention.objects.create(
            sitting=self.sitting,
            verbatim_quote="SJK(T) Ladang Bikam",
            page_number=1,
            mp_name="YB Arul",
            mp_constituency="Segamat",
            mp_party="BN",
            mention_type="QUESTION",
            significance=4,
            sentiment="ADVOCATING",
            change_indicator="NEW",
            ai_summary="Summary text.",
        )

    def test_valid_form(self):
        form = MentionReviewForm(
            data={
                "mp_name": "YB Arul",
                "mp_constituency": "Segamat",
                "mp_party": "BN",
                "mention_type": "QUESTION",
                "significance": 4,
                "sentiment": "ADVOCATING",
                "change_indicator": "NEW",
                "ai_summary": "Summary text.",
                "review_notes": "",
            },
            instance=self.mention,
        )
        self.assertTrue(form.is_valid())

    def test_empty_optional_fields(self):
        """Choice fields are optional — blank is valid."""
        form = MentionReviewForm(
            data={
                "mp_name": "YB Arul",
                "mp_constituency": "Segamat",
                "mp_party": "BN",
                "mention_type": "",
                "significance": "",
                "sentiment": "",
                "change_indicator": "",
                "ai_summary": "",
                "review_notes": "",
            },
            instance=self.mention,
        )
        self.assertTrue(form.is_valid())

    def test_saves_edits(self):
        form = MentionReviewForm(
            data={
                "mp_name": "YB Arulkumar",
                "mp_constituency": "Segamat",
                "mp_party": "BN",
                "mention_type": "BUDGET",
                "significance": 5,
                "sentiment": "PROMISING",
                "change_indicator": "ESCALATION",
                "ai_summary": "Updated summary.",
                "review_notes": "Reviewer correction.",
            },
            instance=self.mention,
        )
        self.assertTrue(form.is_valid())
        saved = form.save()
        self.assertEqual(saved.mp_name, "YB Arulkumar")
        self.assertEqual(saved.mention_type, "BUDGET")
        self.assertEqual(saved.significance, 5)

    def test_invalid_mention_type_rejected(self):
        form = MentionReviewForm(
            data={
                "mp_name": "YB Arul",
                "mp_constituency": "Segamat",
                "mp_party": "BN",
                "mention_type": "INVALID_TYPE",
                "ai_summary": "",
                "review_notes": "",
            },
            instance=self.mention,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("mention_type", form.errors)
