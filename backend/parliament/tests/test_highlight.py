"""Tests for the highlight_keywords template filter."""

from django.test import TestCase

from parliament.templatetags.highlight import highlight_keywords


class HighlightKeywordsTests(TestCase):
    """Test keyword highlighting in Hansard text."""

    def test_sjkt_with_parentheses(self):
        result = highlight_keywords("Funding for SJK(T) schools.")
        self.assertIn("<mark>SJK(T)</mark>", result)

    def test_sjkt_without_parentheses(self):
        result = highlight_keywords("Visit to SJKT Ladang Bikam.")
        self.assertIn("<mark>SJKT</mark>", result)

    def test_dotted_variant(self):
        result = highlight_keywords("The S.J.K.(T) was mentioned.")
        self.assertIn("<mark>S.J.K.(T)</mark>", result)

    def test_sekolah_jenis_kebangsaan_tamil(self):
        result = highlight_keywords(
            "Sekolah Jenis Kebangsaan Tamil Ladang Bikam"
        )
        self.assertIn("<mark>Sekolah Jenis Kebangsaan Tamil</mark>", result)

    def test_sekolah_jenis_kebangsaan_parenthesised(self):
        result = highlight_keywords(
            "Sekolah Jenis Kebangsaan (Tamil)"
        )
        self.assertIn("<mark>Sekolah Jenis Kebangsaan (Tamil)</mark>", result)

    def test_sekolah_tamil(self):
        result = highlight_keywords("Sekolah Tamil di kawasan ini.")
        self.assertIn("<mark>Sekolah Tamil</mark>", result)

    def test_case_insensitive(self):
        result = highlight_keywords("sjk(t) in lower case.")
        self.assertIn("<mark>sjk(t)</mark>", result)

    def test_no_match_left_alone(self):
        text = "No Tamil school keywords here."
        result = highlight_keywords(text)
        self.assertNotIn("<mark>", result)
        self.assertEqual(result, text)

    def test_multiple_matches(self):
        text = "SJK(T) Ladang and SJKT Sentul both."
        result = highlight_keywords(text)
        self.assertEqual(result.count("<mark>"), 2)

    def test_empty_string(self):
        self.assertEqual(highlight_keywords(""), "")

    def test_none_input(self):
        self.assertEqual(highlight_keywords(None), "")

    def test_sjk_space_t(self):
        """SJK (T) with space before parenthesis."""
        result = highlight_keywords("SJK (T) Ladang Bikam")
        self.assertIn("<mark>SJK (T)</mark>", result)
