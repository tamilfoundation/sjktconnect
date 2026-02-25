"""Tests for Hansard text normaliser."""

from django.test import TestCase

from hansard.pipeline.normalizer import normalize_text


class NormalizeTextTests(TestCase):
    """Test normalize_text handles all SJK(T) variants."""

    def test_empty_string(self):
        self.assertEqual(normalize_text(""), "")

    def test_none_returns_empty(self):
        self.assertEqual(normalize_text(None), "")

    def test_lowercase(self):
        result = normalize_text("SEKOLAH JENIS KEBANGSAAN TAMIL")
        self.assertEqual(result, "sekolah jenis kebangsaan tamil")

    def test_whitespace_collapse(self):
        result = normalize_text("SJK(T)  Ladang\n\nBikam")
        self.assertIn("sjk(t) ladang bikam", result)

    def test_sjkt_without_brackets(self):
        """SJKT (no brackets) should normalise to sjk(t)."""
        result = normalize_text("SJKT Ladang Bikam")
        self.assertIn("sjk(t)", result)

    def test_sjkt_inside_word_not_replaced(self):
        """SJKT inside a longer word should not be replaced."""
        result = normalize_text("some_sjkt_thing")
        # Word boundary check — should not replace inside compound
        self.assertNotIn("sjk(t)", result)

    def test_s_j_k_t_dotted(self):
        """S.J.K.(T) should normalise to sjk(t)."""
        result = normalize_text("S.J.K.(T) Ladang Bikam")
        self.assertIn("sjk(t)", result)

    def test_s_j_k_t_dotted_no_final_dot(self):
        """S.J.K(T) (no dot before bracket) should normalise to sjk(t)."""
        result = normalize_text("S.J.K(T) Ladang Bikam")
        self.assertIn("sjk(t)", result)

    def test_sjk_t_already_correct(self):
        """SJK(T) in original form should stay as sjk(t)."""
        result = normalize_text("SJK(T) Ladang Bikam")
        self.assertIn("sjk(t)", result)

    def test_unicode_nfkc(self):
        """Non-breaking spaces and other Unicode oddities should be normalised."""
        # \xa0 is non-breaking space
        result = normalize_text("SJK(T)\xa0Ladang")
        self.assertIn("sjk(t) ladang", result)

    def test_mixed_variants_in_one_text(self):
        """Multiple variants in the same text should all normalise."""
        text = "SJKT schools and S.J.K.(T) schools and SJK(T) schools"
        result = normalize_text(text)
        # All three should become sjk(t)
        self.assertEqual(result.count("sjk(t)"), 3)

    def test_sekolah_tamil_preserved(self):
        """'Sekolah Tamil' should be lowercased but otherwise preserved."""
        result = normalize_text("Sekolah Tamil di Ladang Bikam")
        self.assertIn("sekolah tamil", result)

    def test_tabs_and_newlines(self):
        result = normalize_text("line one\tword\nline two")
        self.assertEqual(result, "line one word line two")
