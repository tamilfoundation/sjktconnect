"""Tests for stop_words module."""

from django.test import TestCase

from hansard.pipeline.stop_words import STOP_WORDS, remove_stop_words


class RemoveStopWordsTests(TestCase):
    """Test stop word removal for fuzzy matching."""

    def test_removes_school_prefixes(self):
        result = remove_stop_words("sjk(t) ladang bikam")
        self.assertNotIn("sjk(t)", result)
        self.assertIn("bikam", result)

    def test_removes_location_words(self):
        result = remove_stop_words("ladang bukit raja")
        self.assertNotIn("ladang", result)
        self.assertIn("bukit", result)
        self.assertIn("raja", result)

    def test_preserves_distinctive_words(self):
        result = remove_stop_words("bikam")
        self.assertEqual(result, "bikam")

    def test_empty_after_removal(self):
        result = remove_stop_words("sjk(t) sekolah tamil")
        self.assertEqual(result, "")

    def test_empty_input(self):
        result = remove_stop_words("")
        self.assertEqual(result, "")

    def test_stop_words_are_lowercase(self):
        for word in STOP_WORDS:
            self.assertEqual(word, word.lower(), f"Stop word '{word}' should be lowercase")

    def test_multiple_stop_words_collapsed(self):
        result = remove_stop_words("sjk(t) sekolah jenis kebangsaan tamil ladang bikam")
        self.assertEqual(result, "bikam")
