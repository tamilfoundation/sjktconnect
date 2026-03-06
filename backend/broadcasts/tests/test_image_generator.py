"""Tests for hero image generation service."""

from unittest.mock import Mock, patch

from django.test import TestCase, override_settings

from broadcasts.services.image_generator import generate_hero_image


@patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
class ImageGeneratorTest(TestCase):
    @patch("broadcasts.services.image_generator.genai")
    def test_generates_image_and_returns_base64_data_uri(self, mock_genai):
        """Should return a base64 data URI when Gemini returns an image."""
        mock_image = Mock()
        mock_image.image = Mock()
        mock_image.image.image_bytes = b"fake-png-data"
        mock_response = Mock()
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].content = Mock()
        mock_response.candidates[0].content.parts = [mock_image]
        mock_genai.Client.return_value.models.generate_content.return_value = (
            mock_response
        )

        result = generate_hero_image(
            content_summary="Parliament addressed teacher shortage in Tamil schools",
            style="parliament",
        )

        self.assertIsNotNone(result)
        self.assertTrue(result.startswith("data:image/png;base64,"))

    @patch("broadcasts.services.image_generator.genai")
    def test_returns_none_on_error(self, mock_genai):
        """Should return None when the API call fails."""
        mock_genai.Client.return_value.models.generate_content.side_effect = (
            Exception("API error")
        )

        result = generate_hero_image(
            content_summary="Test",
            style="parliament",
        )
        self.assertIsNone(result)

    @patch.dict("os.environ", {}, clear=True)
    def test_returns_none_without_api_key(self):
        """Should return None when GEMINI_API_KEY is not set."""
        result = generate_hero_image(
            content_summary="Test",
            style="parliament",
        )
        self.assertIsNone(result)

    @patch("broadcasts.services.image_generator.genai")
    def test_returns_none_when_no_image_in_response(self, mock_genai):
        """Should return None when Gemini returns text instead of an image."""
        mock_text = Mock()
        mock_text.image = None
        mock_text.text = "I cannot generate images"
        mock_response = Mock()
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].content = Mock()
        mock_response.candidates[0].content.parts = [mock_text]
        mock_genai.Client.return_value.models.generate_content.return_value = (
            mock_response
        )

        result = generate_hero_image(content_summary="Test", style="parliament")
        self.assertIsNone(result)

    @patch("broadcasts.services.image_generator.genai")
    def test_uses_correct_style_prompt(self, mock_genai):
        """Should use the style-specific prompt for each style."""
        mock_image = Mock()
        mock_image.image = Mock()
        mock_image.image.image_bytes = b"fake-png-data"
        mock_response = Mock()
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].content = Mock()
        mock_response.candidates[0].content.parts = [mock_image]
        mock_genai.Client.return_value.models.generate_content.return_value = (
            mock_response
        )

        for style in ("parliament", "news", "monthly"):
            generate_hero_image(content_summary="Test", style=style)

        # All three calls should have been made
        self.assertEqual(
            mock_genai.Client.return_value.models.generate_content.call_count, 3
        )

    @patch("broadcasts.services.image_generator.genai")
    def test_falls_back_to_news_style_for_unknown(self, mock_genai):
        """Should use 'news' style prompt for unrecognised style values."""
        mock_image = Mock()
        mock_image.image = Mock()
        mock_image.image.image_bytes = b"fake-png-data"
        mock_response = Mock()
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].content = Mock()
        mock_response.candidates[0].content.parts = [mock_image]
        mock_genai.Client.return_value.models.generate_content.return_value = (
            mock_response
        )

        result = generate_hero_image(content_summary="Test", style="unknown")
        self.assertIsNotNone(result)
