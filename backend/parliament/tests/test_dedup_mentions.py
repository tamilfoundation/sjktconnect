"""Tests for dedup_mentions command."""
from datetime import date

from django.test import TestCase
from django.core.management import call_command

from hansard.models import HansardMention, HansardSitting


class DedupSameSpeakerTest(TestCase):
    def setUp(self):
        self.sitting = HansardSitting.objects.create(
            sitting_date=date(2025, 10, 29),
            pdf_url="https://example.com/test.pdf",
            status="COMPLETED",
            mention_count=3,
        )

    def test_dedup_same_speaker_same_page(self):
        """Mentions with same mp_name and page_number should be merged."""
        HansardMention.objects.create(
            sitting=self.sitting, page_number=5, mp_name="YB Ahmad",
            keyword_matched="SJK(T)", verbatim_quote="Short quote",
            ai_summary="Summary 1", significance=2,
        )
        HansardMention.objects.create(
            sitting=self.sitting, page_number=5, mp_name="YB Ahmad",
            keyword_matched="SJK(T)", verbatim_quote="A much longer quote about schools",
            ai_summary="Summary 2", significance=3,
        )
        HansardMention.objects.create(
            sitting=self.sitting, page_number=5, mp_name="YB Bala",
            keyword_matched="SJK(T)", verbatim_quote="Different speaker",
            ai_summary="Summary 3", significance=2,
        )
        call_command("dedup_mentions")
        remaining = HansardMention.objects.filter(sitting=self.sitting).count()
        # YB Ahmad's 2 mentions merged into 1, YB Bala stays = 2 total
        self.assertEqual(remaining, 2)

    def test_dedup_keeps_highest_significance(self):
        """Keeper should have highest significance."""
        HansardMention.objects.create(
            sitting=self.sitting, page_number=5, mp_name="YB Ahmad",
            keyword_matched="SJK(T)", verbatim_quote="Short",
            ai_summary="Low", significance=1,
        )
        HansardMention.objects.create(
            sitting=self.sitting, page_number=5, mp_name="YB Ahmad",
            keyword_matched="SJK(T)", verbatim_quote="Much longer quote here",
            ai_summary="High", significance=4,
        )
        call_command("dedup_mentions")
        keeper = HansardMention.objects.get(sitting=self.sitting)
        self.assertEqual(keeper.significance, 4)
