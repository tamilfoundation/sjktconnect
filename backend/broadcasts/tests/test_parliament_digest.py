from unittest.mock import patch, Mock
from django.test import TestCase
from parliament.models import ParliamentaryMeeting
from broadcasts.services.parliament_digest import generate_parliament_digest


class ParliamentDigestTest(TestCase):
    def setUp(self):
        self.meeting = ParliamentaryMeeting.objects.create(
            name="First Meeting of the Fourth Term 2026",
            short_name="1st Meeting 2026",
            term=4, session=1, year=2026,
            start_date="2026-02-24",
            end_date="2026-03-20",
            report_html="<h2>Executive Summary</h2><p>Five Tamil schools discussed...</p>",
            executive_summary="Five Tamil schools were discussed across 12 sittings.",
            is_published=True,
        )

    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    @patch("broadcasts.services.parliament_digest.genai")
    def test_generates_action_oriented_content(self, mock_genai):
        mock_response = Mock()
        mock_response.text = '{"headlines": "Parliament addressed Tamil school funding.", "developments": [{"topic": "Funding", "summary": "YB X raised RM2M allocation.", "actions": {"school_boards": "Write to your PPD.", "parents": "Ask your school about the allocation.", "ngos": "Submit memo to Education Ministry.", "community": "Share with school WhatsApp group."}}], "scorecard_summary": "3 MPs spoke up.", "one_thing": "Contact your MP."}'
        mock_genai.Client.return_value.models.generate_content.return_value = mock_response

        result = generate_parliament_digest(self.meeting)

        self.assertIn("headlines", result)
        self.assertIn("developments", result)
        self.assertIn("one_thing", result)
        self.assertIsInstance(result["developments"], list)
        self.assertIn("actions", result["developments"][0])
        self.assertIn("school_boards", result["developments"][0]["actions"])

    def test_returns_none_if_no_report(self):
        self.meeting.report_html = ""
        self.meeting.save()
        result = generate_parliament_digest(self.meeting)
        self.assertIsNone(result)

    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    @patch("broadcasts.services.parliament_digest.genai")
    def test_returns_none_on_invalid_json(self, mock_genai):
        mock_response = Mock()
        mock_response.text = "not json"
        mock_genai.Client.return_value.models.generate_content.return_value = mock_response

        result = generate_parliament_digest(self.meeting)
        self.assertIsNone(result)

    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    @patch("broadcasts.services.parliament_digest.genai")
    def test_returns_none_on_missing_keys(self, mock_genai):
        mock_response = Mock()
        mock_response.text = '{"headlines": "test"}'
        mock_genai.Client.return_value.models.generate_content.return_value = mock_response

        result = generate_parliament_digest(self.meeting)
        self.assertIsNone(result)
