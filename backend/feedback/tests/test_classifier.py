from unittest.mock import Mock, patch

from django.test import TestCase

from feedback.models import InboundEmail
from feedback.services.classifier import classify_email


@patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
class ClassifierTest(TestCase):
    def setUp(self):
        self.email = InboundEmail.objects.create(
            gmail_message_id="msg_001",
            from_email="reader@example.com",
            subject="Re: Parliament Watch",
            body_text="You got the school name wrong. It's SJK(T) Ladang Bikam, not Bikam Estate.",
        )

    @patch("feedback.services.classifier.genai")
    def test_classifies_correction(self, mock_genai):
        mock_response = Mock()
        mock_response.text = '{"classification": "CORRECTION", "reasoning": "Subscriber correcting a school name.", "escalate": false}'
        mock_genai.Client.return_value.models.generate_content.return_value = mock_response

        classify_email(self.email)
        self.email.refresh_from_db()

        self.assertEqual(self.email.classification, "CORRECTION")
        self.assertFalse(self.email.escalated)

    @patch("feedback.services.classifier.genai")
    def test_escalates_when_needed(self, mock_genai):
        mock_response = Mock()
        mock_response.text = '{"classification": "QUESTION", "reasoning": "Complex policy question.", "escalate": true}'
        mock_genai.Client.return_value.models.generate_content.return_value = mock_response

        classify_email(self.email)
        self.email.refresh_from_db()

        self.assertTrue(self.email.escalated)
        self.assertEqual(self.email.response_status, "ESCALATED")

    @patch("feedback.services.classifier.genai")
    def test_handles_invalid_classification(self, mock_genai):
        mock_response = Mock()
        mock_response.text = '{"classification": "INVALID_TYPE", "reasoning": "test", "escalate": false}'
        mock_genai.Client.return_value.models.generate_content.return_value = mock_response

        classify_email(self.email)
        self.email.refresh_from_db()
        self.assertEqual(self.email.classification, "UNCLASSIFIED")

    @patch("feedback.services.classifier.genai")
    def test_handles_json_error(self, mock_genai):
        mock_response = Mock()
        mock_response.text = "not json"
        mock_genai.Client.return_value.models.generate_content.return_value = mock_response

        classify_email(self.email)
        self.email.refresh_from_db()
        self.assertEqual(self.email.classification, "UNCLASSIFIED")
