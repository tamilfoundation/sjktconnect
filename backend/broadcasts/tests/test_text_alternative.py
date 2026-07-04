"""Tests for the HTML → plain-text alternative helper (Sprint 33
audit follow-up).
"""

from django.test import TestCase

from broadcasts.services.text_alternative import html_to_text_alternative


class HtmlToTextAlternativeTest(TestCase):
    def test_empty_input_returns_empty(self):
        self.assertEqual(html_to_text_alternative(""), "")
        self.assertEqual(html_to_text_alternative(None), "")

    def test_style_body_is_stripped(self):
        """Regression: raw CSS rule text used to end up in text_content
        because strip_tags removes <style> tags but keeps their contents.
        """
        html = (
            "<html><head><style>body { font-family: Arial; color: red; }"
            ".foo { padding: 10px; }</style></head>"
            "<body><p>Real content here.</p></body></html>"
        )
        text = html_to_text_alternative(html)
        self.assertNotIn("font-family", text)
        self.assertNotIn("padding", text)
        self.assertIn("Real content here.", text)

    def test_script_body_is_stripped(self):
        html = (
            "<html><body>"
            "<script>alert('boo');console.log('spam');</script>"
            "<p>Story text.</p></body></html>"
        )
        text = html_to_text_alternative(html)
        self.assertNotIn("alert", text)
        self.assertNotIn("console.log", text)
        self.assertIn("Story text.", text)

    def test_head_meta_and_title_stripped(self):
        html = (
            "<html><head><title>Subject line</title>"
            "<meta charset=\"utf-8\"></head>"
            "<body><h1>Actual heading</h1><p>Body.</p></body></html>"
        )
        text = html_to_text_alternative(html)
        self.assertNotIn("Subject line", text)
        self.assertIn("Actual heading", text)
        self.assertIn("Body.", text)

    def test_multiple_blank_lines_collapsed(self):
        html = "<p>One</p>\n\n\n\n\n<p>Two</p>\n\n\n\n\n<p>Three</p>"
        text = html_to_text_alternative(html)
        # No run of more than 2 consecutive newlines.
        self.assertNotIn("\n\n\n", text)

    def test_whitespace_runs_collapsed(self):
        html = "<p>Word1     Word2\t\t\tWord3</p>"
        text = html_to_text_alternative(html)
        self.assertIn("Word1 Word2 Word3", text)
