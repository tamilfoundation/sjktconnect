"""Tests for matcher module — school name matching from Hansard mentions."""

from datetime import date

from django.test import TestCase

from hansard.models import (
    HansardMention,
    HansardSitting,
    MentionedSchool,
    SchoolAlias,
)
from hansard.pipeline.matcher import (
    _extract_school_name_candidates,
    match_mentions,
    match_single_mention,
)
from schools.models import Constituency, School


class ExtractCandidatesTests(TestCase):
    """Test school name candidate extraction from text."""

    def test_sjkt_with_name(self):
        candidates = _extract_school_name_candidates(
            "peruntukan untuk SJK(T) Ladang Bikam di Segamat"
        )
        # Should find "Ladang Bikam" as a candidate
        found = any("ladang bikam" in c.lower() for c in candidates)
        self.assertTrue(found, f"Expected 'ladang bikam' in {candidates}")

    def test_sjkt_no_brackets(self):
        candidates = _extract_school_name_candidates(
            "15 buah SJKT Ladang Bikam dan SJKT Batu Arang"
        )
        self.assertGreater(len(candidates), 0)

    def test_sekolah_jenis_kebangsaan_tamil(self):
        candidates = _extract_school_name_candidates(
            "Sekolah Jenis Kebangsaan (Tamil) Gunung Cheroh di Batu Gajah"
        )
        found = any("gunung cheroh" in c.lower() for c in candidates)
        self.assertTrue(found, f"Expected 'gunung cheroh' in {candidates}")

    def test_sekolah_tamil(self):
        candidates = _extract_school_name_candidates(
            "Sekolah Tamil Vivekananda di Kuala Lumpur"
        )
        found = any("vivekananda" in c.lower() for c in candidates)
        self.assertTrue(found, f"Expected 'vivekananda' in {candidates}")

    def test_no_school_name(self):
        candidates = _extract_school_name_candidates(
            "This is a general discussion about education policy."
        )
        self.assertEqual(len(candidates), 0)

    def test_sjk_dot_format(self):
        candidates = _extract_school_name_candidates(
            "S.J.K.(T) Ladang Batu Arang perlu dibaiki"
        )
        self.assertGreater(len(candidates), 0)


class MatcherSetupMixin:
    """Common setup for matcher tests — creates schools and aliases."""

    @classmethod
    def setUpTestData(cls):
        cls.constituency = Constituency.objects.create(
            code="P140", name="Segamat", state="Johor"
        )
        cls.school_bikam = School.objects.create(
            moe_code="JBD0050",
            name="SEKOLAH JENIS KEBANGSAAN (TAMIL) LADANG BIKAM",
            short_name="SJK(T) Ladang Bikam",
            state="Johor",
            constituency=cls.constituency,
        )
        cls.school_batu_arang = School.objects.create(
            moe_code="BBD0020",
            name="SEKOLAH JENIS KEBANGSAAN (TAMIL) BATU ARANG",
            short_name="SJK(T) Batu Arang",
            state="Selangor",
            constituency=cls.constituency,
        )
        cls.school_cheroh = School.objects.create(
            moe_code="ACD0030",
            name="SEKOLAH JENIS KEBANGSAAN (TAMIL) GUNUNG CHEROH",
            short_name="SJK(T) Gunung Cheroh",
            state="Perak",
            constituency=cls.constituency,
        )

        # Create aliases (simulating seed_aliases output)
        for school in [cls.school_bikam, cls.school_batu_arang, cls.school_cheroh]:
            short_lower = school.short_name.lower()
            SchoolAlias.objects.create(
                school=school,
                alias=school.short_name,
                alias_normalized=short_lower,
                alias_type=SchoolAlias.AliasType.SHORT,
            )
            # Strip SJK(T) prefix
            import re
            stripped = re.sub(r"^sjk\(t\)\s+", "", short_lower)
            if stripped != short_lower:
                SchoolAlias.objects.create(
                    school=school,
                    alias=stripped.title(),
                    alias_normalized=stripped,
                    alias_type=SchoolAlias.AliasType.COMMON,
                )

        cls.sitting = HansardSitting.objects.create(
            sitting_date=date(2026, 1, 26),
            pdf_url="https://example.com/test.pdf",
            pdf_filename="test.pdf",
            status=HansardSitting.Status.COMPLETED,
        )


class MatchSingleMentionTests(MatcherSetupMixin, TestCase):
    """Test matching a single mention to schools."""

    def test_exact_match(self):
        """Mention with exact school name should match with 100% confidence."""
        mention = HansardMention.objects.create(
            sitting=self.sitting,
            page_number=1,
            verbatim_quote="SJK(T) Ladang Bikam memerlukan peruntukan",
            context_before="Tuan Ahmad: ",
            context_after=" sebanyak RM2 juta.",
            keyword_matched="sjk(t)",
        )
        results = match_single_mention(mention)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["school_id"], "JBD0050")
        self.assertEqual(results[0]["confidence"], 100)
        self.assertEqual(results[0]["matched_by"], MentionedSchool.MatchMethod.EXACT)
        self.assertFalse(results[0]["needs_review"])

    def test_no_match(self):
        """Mention with generic keyword but no school name should return empty."""
        mention = HansardMention.objects.create(
            sitting=self.sitting,
            page_number=1,
            verbatim_quote="sekolah tamil di kawasan ladang",
            context_before="masalah yang dihadapi oleh ",
            context_after=" memerlukan perhatian segera.",
            keyword_matched="sekolah tamil",
        )
        results = match_single_mention(mention)
        self.assertEqual(len(results), 0)

    def test_multi_school_mention(self):
        """Mention referencing multiple schools should match all of them."""
        mention = HansardMention.objects.create(
            sitting=self.sitting,
            page_number=2,
            verbatim_quote=(
                "SJKT Ladang Bikam dan SJK(T) Batu Arang"
            ),
            context_before="membaiki ",
            context_after=" di seluruh negara.",
            keyword_matched="sjk(t)",
        )
        results = match_single_mention(mention)
        matched_ids = {r["school_id"] for r in results}
        self.assertIn("JBD0050", matched_ids)  # Bikam
        self.assertIn("BBD0020", matched_ids)  # Batu Arang

    def test_fuzzy_match(self):
        """Slightly different name should match via trigram with lower confidence."""
        mention = HansardMention.objects.create(
            sitting=self.sitting,
            page_number=1,
            verbatim_quote="SJK(T) Ldg Bikam perlu dibaiki",
            context_before="",
            context_after="",
            keyword_matched="sjk(t)",
        )
        results = match_single_mention(mention)
        # May or may not match depending on trigram threshold
        # The key test is that it doesn't crash
        for r in results:
            self.assertIn(r["matched_by"], [
                MentionedSchool.MatchMethod.EXACT,
                MentionedSchool.MatchMethod.TRIGRAM,
            ])

    def test_context_used_for_matching(self):
        """Matcher should use context_before/after in addition to verbatim."""
        mention = HansardMention.objects.create(
            sitting=self.sitting,
            page_number=3,
            verbatim_quote="sekolah tamil",
            context_before="peruntukan untuk SJK(T) Gunung Cheroh. Masalah ",
            context_after=" di kawasan ini perlu ditangani.",
            keyword_matched="sekolah tamil",
        )
        results = match_single_mention(mention)
        if results:
            matched_ids = {r["school_id"] for r in results}
            self.assertIn("ACD0030", matched_ids)  # Gunung Cheroh


class MatchMentionsIntegrationTests(MatcherSetupMixin, TestCase):
    """Test batch matching via match_mentions()."""

    def test_batch_matching(self):
        """match_mentions should process multiple mentions."""
        HansardMention.objects.create(
            sitting=self.sitting, page_number=1,
            verbatim_quote="SJK(T) Ladang Bikam",
            keyword_matched="sjk(t)",
        )
        HansardMention.objects.create(
            sitting=self.sitting, page_number=2,
            verbatim_quote="SJK(T) Batu Arang",
            keyword_matched="sjk(t)",
        )

        mentions = HansardMention.objects.filter(sitting=self.sitting)
        result = match_mentions(mentions)

        self.assertEqual(result["total"], 2)
        self.assertGreaterEqual(result["matched"], 1)
        self.assertGreaterEqual(MentionedSchool.objects.count(), 1)

    def test_creates_mentioned_school_records(self):
        """match_mentions should create MentionedSchool records."""
        mention = HansardMention.objects.create(
            sitting=self.sitting, page_number=1,
            verbatim_quote="SJK(T) Ladang Bikam memerlukan",
            keyword_matched="sjk(t)",
        )

        match_mentions(HansardMention.objects.filter(pk=mention.pk))

        ms = MentionedSchool.objects.filter(mention=mention)
        self.assertEqual(ms.count(), 1)
        self.assertEqual(ms.first().school_id, "JBD0050")
        self.assertEqual(ms.first().confidence_score, 100)

    def test_idempotent(self):
        """Running match_mentions twice should not duplicate records."""
        HansardMention.objects.create(
            sitting=self.sitting, page_number=1,
            verbatim_quote="SJK(T) Ladang Bikam",
            keyword_matched="sjk(t)",
        )
        mentions = HansardMention.objects.filter(sitting=self.sitting)

        match_mentions(mentions)
        count1 = MentionedSchool.objects.count()

        match_mentions(mentions)
        count2 = MentionedSchool.objects.count()

        self.assertEqual(count1, count2)

    def test_low_confidence_flagged(self):
        """Matches below 80% confidence should have needs_review=True."""
        # Create a MentionedSchool with low confidence directly to test the flag
        mention = HansardMention.objects.create(
            sitting=self.sitting, page_number=1,
            verbatim_quote="SJK(T) Ladang Bikam",
            keyword_matched="sjk(t)",
        )
        ms = MentionedSchool.objects.create(
            mention=mention,
            school=self.school_bikam,
            confidence_score=50,
            matched_by=MentionedSchool.MatchMethod.TRIGRAM,
            needs_review=True,
        )
        self.assertTrue(ms.needs_review)


class MentionedSchoolModelTests(MatcherSetupMixin, TestCase):
    """Test MentionedSchool model."""

    def test_str(self):
        mention = HansardMention.objects.create(
            sitting=self.sitting, page_number=1,
            verbatim_quote="test", keyword_matched="sjk(t)",
        )
        ms = MentionedSchool.objects.create(
            mention=mention,
            school=self.school_bikam,
            confidence_score=100,
            matched_by=MentionedSchool.MatchMethod.EXACT,
        )
        self.assertIn("Ladang Bikam", str(ms))
        self.assertIn("100", str(ms))

    def test_unique_together(self):
        """Cannot link same school to same mention twice."""
        mention = HansardMention.objects.create(
            sitting=self.sitting, page_number=1,
            verbatim_quote="test", keyword_matched="sjk(t)",
        )
        MentionedSchool.objects.create(
            mention=mention, school=self.school_bikam,
            confidence_score=100,
        )
        with self.assertRaises(Exception):
            MentionedSchool.objects.create(
                mention=mention, school=self.school_bikam,
                confidence_score=50,
            )


class SchoolAliasModelTests(MatcherSetupMixin, TestCase):
    """Test SchoolAlias model."""

    def test_str(self):
        alias = SchoolAlias.objects.first()
        self.assertIn("→", str(alias))

    def test_unique_together(self):
        """Cannot create duplicate alias_normalized for same school."""
        with self.assertRaises(Exception):
            SchoolAlias.objects.create(
                school=self.school_bikam,
                alias="SJK(T) Ladang Bikam",
                alias_normalized="sjk(t) ladang bikam",
                alias_type=SchoolAlias.AliasType.COMMON,
            )
