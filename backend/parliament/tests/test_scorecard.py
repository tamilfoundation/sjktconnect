"""Tests for scorecard aggregation service."""

from datetime import date

from django.test import TestCase

from hansard.models import HansardMention, HansardSitting
from parliament.models import MPScorecard
from parliament.services.scorecard import _resolve_constituency, update_all_scorecards
from schools.models import Constituency, School


class ResolveConcuencyTests(TestCase):
    """Test constituency lookup by name."""

    def setUp(self):
        self.constituency = Constituency.objects.create(
            code="P140",
            name="Segamat",
            state="Johor",
        )

    def test_exact_match(self):
        result = _resolve_constituency("Segamat")
        self.assertEqual(result, self.constituency)

    def test_case_insensitive(self):
        result = _resolve_constituency("segamat")
        self.assertEqual(result, self.constituency)

    def test_empty_returns_none(self):
        self.assertIsNone(_resolve_constituency(""))
        self.assertIsNone(_resolve_constituency(None))

    def test_code_name_pattern(self):
        result = _resolve_constituency("P140 Segamat")
        self.assertEqual(result, self.constituency)

    def test_unknown_returns_none(self):
        self.assertIsNone(_resolve_constituency("NonExistent"))


class UpdateAllScorecardsTests(TestCase):
    """Test full scorecard recalculation.

    Scenario: 5 mentions for 2 MPs across 2 sittings.
    MP A: 3 mentions (2 substantive sig>=3, 1 question, 1 promising)
    MP B: 2 mentions (1 substantive sig>=3, 0 questions)
    """

    def setUp(self):
        self.constituency_a = Constituency.objects.create(
            code="P140", name="Segamat", state="Johor",
        )
        self.constituency_b = Constituency.objects.create(
            code="P001", name="Padang Besar", state="Perlis",
        )

        # Schools in constituency A
        School.objects.create(
            moe_code="JBD0050",
            name="SJK(T) Test School A",
            short_name="SJK(T) Test A",
            state="Johor",
            constituency=self.constituency_a,
            enrolment=150,
        )
        School.objects.create(
            moe_code="JBD0051",
            name="SJK(T) Test School B",
            short_name="SJK(T) Test B",
            state="Johor",
            constituency=self.constituency_a,
            enrolment=200,
        )

        sitting1 = HansardSitting.objects.create(
            sitting_date="2026-01-26",
            pdf_url="https://example.com/1.pdf",
            pdf_filename="1.pdf",
        )
        sitting2 = HansardSitting.objects.create(
            sitting_date="2026-02-10",
            pdf_url="https://example.com/2.pdf",
            pdf_filename="2.pdf",
        )

        # MP A: 3 mentions
        HansardMention.objects.create(
            sitting=sitting1, verbatim_quote="Q1", page_number=1,
            mp_name="YB Arul", mp_constituency="Segamat", mp_party="BN",
            mention_type="QUESTION", significance=4, sentiment="ADVOCATING",
            change_indicator="NEW",
        )
        HansardMention.objects.create(
            sitting=sitting1, verbatim_quote="Q2", page_number=5,
            mp_name="YB Arul", mp_constituency="Segamat", mp_party="BN",
            mention_type="BUDGET", significance=3, sentiment="PROMISING",
            change_indicator="NEW",
        )
        HansardMention.objects.create(
            sitting=sitting2, verbatim_quote="Q3", page_number=10,
            mp_name="YB Arul", mp_constituency="Segamat", mp_party="BN",
            mention_type="THROWAWAY", significance=1, sentiment="NEUTRAL",
            change_indicator="REPEAT",
        )

        # MP B: 2 mentions
        HansardMention.objects.create(
            sitting=sitting1, verbatim_quote="Q4", page_number=20,
            mp_name="YB Kumar", mp_constituency="Padang Besar", mp_party="PH",
            mention_type="POLICY", significance=3, sentiment="NEUTRAL",
            change_indicator="NEW",
        )
        HansardMention.objects.create(
            sitting=sitting2, verbatim_quote="Q5", page_number=30,
            mp_name="YB Kumar", mp_constituency="Padang Besar", mp_party="PH",
            mention_type="OTHER", significance=2, sentiment="DEFLECTING",
            change_indicator="REPEAT",
        )

    def test_correct_number_of_scorecards(self):
        result = update_all_scorecards()
        self.assertEqual(result["created"], 2)
        self.assertEqual(MPScorecard.objects.count(), 2)

    def test_mp_a_totals(self):
        update_all_scorecards()
        card = MPScorecard.objects.get(mp_name="YB Arul")
        self.assertEqual(card.total_mentions, 3)
        self.assertEqual(card.substantive_mentions, 2)  # sig >= 3
        self.assertEqual(card.questions_asked, 1)  # type QUESTION
        self.assertEqual(card.commitments_made, 1)  # sentiment PROMISING
        self.assertEqual(card.constituency, self.constituency_a)
        self.assertEqual(card.party, "BN")

    def test_mp_b_totals(self):
        update_all_scorecards()
        card = MPScorecard.objects.get(mp_name="YB Kumar")
        self.assertEqual(card.total_mentions, 2)
        self.assertEqual(card.substantive_mentions, 1)  # sig 3 only
        self.assertEqual(card.questions_asked, 0)
        self.assertEqual(card.commitments_made, 0)

    def test_school_count_from_constituency(self):
        update_all_scorecards()
        card = MPScorecard.objects.get(mp_name="YB Arul")
        self.assertEqual(card.school_count, 2)
        self.assertEqual(card.total_enrolment, 350)

    def test_last_mention_date(self):
        update_all_scorecards()
        card = MPScorecard.objects.get(mp_name="YB Arul")
        self.assertEqual(card.last_mention_date, date(2026, 2, 10))

    def test_idempotent_recalculation(self):
        update_all_scorecards()
        result = update_all_scorecards()
        self.assertEqual(result["created"], 0)
        self.assertEqual(result["updated"], 2)
        self.assertEqual(MPScorecard.objects.count(), 2)

    def test_stale_scorecards_deleted(self):
        update_all_scorecards()
        self.assertEqual(MPScorecard.objects.count(), 2)

        # Delete all mentions for MP B
        HansardMention.objects.filter(mp_name="YB Kumar").delete()
        result = update_all_scorecards()
        self.assertEqual(result["deleted"], 1)
        self.assertEqual(MPScorecard.objects.count(), 1)
        self.assertFalse(MPScorecard.objects.filter(mp_name="YB Kumar").exists())

    def test_no_mentions_returns_zero(self):
        HansardMention.objects.all().delete()
        result = update_all_scorecards()
        self.assertEqual(result["created"], 0)
        self.assertEqual(result["updated"], 0)
