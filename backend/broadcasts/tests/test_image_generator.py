"""Tests for hero image generation service (two-step: scene brief + Nano Banana Pro)."""

from unittest.mock import Mock, patch

from django.test import TestCase

from broadcasts.services.image_generator import generate_hero_image


def _mock_scene_response():
    """Mock Gemini scene brief response (text)."""
    resp = Mock()
    resp.text = "A Tamil school courtyard with children playing"
    return resp


def _mock_image_response():
    """Mock Nano Banana Pro image response (inline_data)."""
    mock_part = Mock()
    mock_part.inline_data = Mock()
    mock_part.inline_data.mime_type = "image/png"
    mock_part.inline_data.data = b"fake-png-data"
    resp = Mock()
    resp.candidates = [Mock()]
    resp.candidates[0].content = Mock()
    resp.candidates[0].content.parts = [mock_part]
    return resp


def _mock_text_only_response():
    """Mock response with no image."""
    mock_part = Mock()
    mock_part.inline_data = None
    resp = Mock()
    resp.candidates = [Mock()]
    resp.candidates[0].content = Mock()
    resp.candidates[0].content.parts = [mock_part]
    return resp


@patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
class ImageGeneratorTest(TestCase):
    @patch("broadcasts.services.image_generator.genai")
    def test_generates_image_and_returns_bytes(self, mock_genai):
        """Should return PNG bytes via two-step generation."""
        client = mock_genai.Client.return_value
        client.models.generate_content.side_effect = [
            _mock_scene_response(),
            _mock_image_response(),
        ]

        result = generate_hero_image(
            content_summary="Parliament addressed teacher shortage",
            style="parliament",
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result, bytes)
        self.assertEqual(result, b"fake-png-data")
        self.assertEqual(client.models.generate_content.call_count, 2)

    @patch("broadcasts.services.image_generator.genai")
    def test_returns_none_on_image_generation_error(self, mock_genai):
        """Should return None when Nano Banana Pro fails."""
        client = mock_genai.Client.return_value
        client.models.generate_content.side_effect = [
            _mock_scene_response(),
            Exception("Image API error"),
        ]

        result = generate_hero_image(content_summary="Test", style="news")
        self.assertIsNone(result)

    @patch.dict("os.environ", {}, clear=True)
    def test_returns_none_without_api_key(self):
        """Should return None when GEMINI_API_KEY is not set."""
        result = generate_hero_image(content_summary="Test", style="parliament")
        self.assertIsNone(result)

    @patch("broadcasts.services.image_generator.genai")
    def test_returns_none_when_no_image_in_response(self, mock_genai):
        """Should return None when Nano Banana Pro returns no image."""
        client = mock_genai.Client.return_value
        client.models.generate_content.side_effect = [
            _mock_scene_response(),
            _mock_text_only_response(),
        ]

        result = generate_hero_image(content_summary="Test", style="parliament")
        self.assertIsNone(result)

    @patch("broadcasts.services.image_generator.genai")
    def test_scene_brief_failure_uses_fallback(self, mock_genai):
        """Should use fallback scene and still generate image if brief fails."""
        client = mock_genai.Client.return_value
        client.models.generate_content.side_effect = [
            Exception("Scene brief failed"),
            _mock_image_response(),
        ]

        result = generate_hero_image(content_summary="Test", style="monthly")
        self.assertIsNotNone(result)
        self.assertEqual(result, b"fake-png-data")

    @patch("broadcasts.services.image_generator.genai")
    def test_handles_base64_string_inline_data(self, mock_genai):
        """Should handle inline_data.data as base64 string (not just bytes)."""
        import base64

        mock_part = Mock()
        mock_part.inline_data = Mock()
        mock_part.inline_data.mime_type = "image/png"
        mock_part.inline_data.data = base64.b64encode(b"fake-png-data").decode()
        img_resp = Mock()
        img_resp.candidates = [Mock()]
        img_resp.candidates[0].content = Mock()
        img_resp.candidates[0].content.parts = [mock_part]

        client = mock_genai.Client.return_value
        client.models.generate_content.side_effect = [
            _mock_scene_response(),
            img_resp,
        ]

        result = generate_hero_image(content_summary="Test", style="news")
        self.assertIsNotNone(result)
        self.assertEqual(result, b"fake-png-data")
