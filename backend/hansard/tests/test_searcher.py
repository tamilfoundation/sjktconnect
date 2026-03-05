"""Tests for Hansard keyword searcher."""

from django.test import TestCase

from hansard.pipeline.searcher import search_keywords


class SearchKeywordsTests(TestCase):
    """Test keyword search against normalised Hansard pages."""

    def _make_pages(self, *texts):
        """Helper to create page tuples."""
        return [(i + 1, text) for i, text in enumerate(texts)]

    def test_single_match(self):
        pages = self._make_pages(
            "The government allocated RM5 million for SJK(T) Ladang Bikam "
            "in the 2026 budget."
        )
        matches = search_keywords(pages, ["sjk(t)"])
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["page_number"], 1)
        self.assertEqual(matches[0]["keyword_matched"], "sjk(t)")

    def test_multiple_matches_same_page(self):
        pages = self._make_pages(
            "SJK(T) Ladang Bikam and SJK(T) Ladang Batu Arang "
            "both received allocations."
        )
        matches = search_keywords(pages, ["sjk(t)"])
        self.assertEqual(len(matches), 2)

    def test_matches_across_pages(self):
        pages = self._make_pages(
            "Page one mentions SJK(T) Ladang Bikam.",
            "Page two has no mentions.",
            "Page three mentions SJK(T) Ladang Batu Arang.",
        )
        matches = search_keywords(pages, ["sjk(t)"])
        self.assertEqual(len(matches), 2)
        self.assertEqual(matches[0]["page_number"], 1)
        self.assertEqual(matches[1]["page_number"], 3)

    def test_no_matches(self):
        pages = self._make_pages(
            "This page discusses SK Taman Universiti and other schools."
        )
        matches = search_keywords(pages, ["sjk(t)", "sekolah tamil"])
        self.assertEqual(len(matches), 0)

    def test_variant_sjkt_normalised(self):
        """SJKT without brackets should be found by sjk(t) keyword."""
        pages = self._make_pages(
            "Tuan Yang di-Pertua, SJKT Ladang Bikam needs repairs."
        )
        matches = search_keywords(pages, ["sjk(t)"])
        self.assertEqual(len(matches), 1)

    def test_variant_dotted(self):
        """S.J.K.(T) should be found."""
        pages = self._make_pages(
            "Tuan Yang di-Pertua, S.J.K.(T) Ladang Bikam needs repairs."
        )
        matches = search_keywords(pages, ["sjk(t)"])
        self.assertEqual(len(matches), 1)

    def test_sekolah_tamil_keyword(self):
        pages = self._make_pages(
            "Kerajaan perlu memberi perhatian kepada sekolah Tamil "
            "di kawasan ladang."
        )
        matches = search_keywords(pages, ["sekolah tamil"])
        self.assertEqual(len(matches), 1)

    def test_multiple_keywords_same_location(self):
        """If text matches multiple keywords, each should produce a match."""
        pages = self._make_pages(
            "SJK(T) schools, also known as sekolah Tamil, need funding."
        )
        matches = search_keywords(pages, ["sjk(t)", "sekolah tamil"])
        self.assertEqual(len(matches), 2)

    def test_context_extraction(self):
        """Matches should include context before and after."""
        prefix = "A" * 100 + " "
        suffix = " " + "B" * 100
        text = prefix + "SJK(T) Ladang Bikam needs repairs." + suffix
        pages = self._make_pages(text)
        matches = search_keywords(pages, ["sjk(t)"])
        self.assertEqual(len(matches), 1)
        # Context should contain some of the A's and B's
        self.assertIn("A", matches[0]["context_before"])
        self.assertIn("B", matches[0]["context_after"])

    def test_verbatim_quote_is_original_text(self):
        """Verbatim quote should preserve original casing."""
        pages = self._make_pages(
            "The SJK(T) LADANG BIKAM school received funding."
        )
        matches = search_keywords(pages, ["sjk(t)"])
        self.assertEqual(len(matches), 1)
        # The verbatim should be from original text, not normalised
        self.assertIn("SJK(T)", matches[0]["verbatim_quote"])

    def test_empty_pages_skipped(self):
        pages = self._make_pages("", "   ", "SJK(T) found here")
        matches = search_keywords(pages, ["sjk(t)"])
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["page_number"], 3)

    def test_case_insensitive(self):
        """Keywords should match regardless of case in source text."""
        pages = self._make_pages("sjk(t) ladang bikam and SJK(T) LADANG BIKAM")
        matches = search_keywords(pages, ["sjk(t)"])
        self.assertEqual(len(matches), 2)

    def test_speaker_extraction_yab(self):
        """YAB title should be captured."""
        pages = self._make_pages(
            "YAB Perdana Menteri [Dato' Sri Anwar Ibrahim]: "
            "Kerajaan akan membaiki SJK(T) di seluruh negara."
        )
        matches = search_keywords(pages, ["sjk(t)"])
        self.assertEqual(len(matches), 1)
        self.assertIn("Anwar Ibrahim", matches[0]["speaker_name"])

    def test_speaker_extraction_dato_seri(self):
        """Dato' Seri title should be captured."""
        pages = self._make_pages(
            "Dato' Seri Dr. Mah Hang Soon [Jempol]: "
            "SJK(T) di kawasan saya memerlukan peruntukan."
        )
        matches = search_keywords(pages, ["sjk(t)"])
        self.assertEqual(len(matches), 1)
        self.assertIn("Mah Hang Soon", matches[0]["speaker_name"])

    def test_speaker_extraction_tuan_pengerusi(self):
        """Tuan Pengerusi is a generic title, should return empty speaker."""
        pages = self._make_pages(
            "Tuan Pengerusi: SJK(T) Ladang Bikam perlu dibaiki."
        )
        matches = search_keywords(pages, ["sjk(t)"])
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["speaker_name"], "")

    def test_speaker_two_pages_back(self):
        """Speaker started 2 pages before the keyword — should still find them."""
        pages = self._make_pages(
            "Tuan Ganabatirau a/l Veraman [Klang]: Saya ingin bertanya...",
            "...sambungan ucapan tentang pendidikan...",
            "...khususnya SJK(T) di kawasan saya."
        )
        matches = search_keywords(pages, ["sjk(t)"])
        self.assertEqual(len(matches), 1)
        self.assertIn("Ganabatirau", matches[0]["speaker_name"])

    def test_speaker_menteri_besar(self):
        """Menteri Besar title should be captured."""
        pages = self._make_pages(
            "Menteri Besar Perak [Dato' Saarani Mohamad]: "
            "Kerajaan negeri akan bantu SJK(T) di Perak."
        )
        matches = search_keywords(pages, ["sjk(t)"])
        self.assertEqual(len(matches), 1)
        self.assertIn("Saarani", matches[0]["speaker_name"])
