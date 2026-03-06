from unittest.mock import Mock, patch

from django.test import TestCase

from feedback.models import InboundEmail
from feedback.services.responder import auto_respond


class ResponderTest(TestCase):
    def setUp(self):
        self.email = InboundEmail.objects.create(
            gmail_message_id="msg_001",
            from_email="reader@example.com",
            from_name="A Reader",
            subject="Re: Parliament Watch",
            body_text="You got the school name wrong.",
            classification="CORRECTION",
        )

    def test_sends_auto_response_for_correction(self):
        """In dev mode (no BREVO_API_KEY), should mark as AUTO_RESPONDED."""
        auto_respond(self.email)
        self.email.refresh_from_db()

        self.assertEqual(self.email.response_status, "AUTO_RESPONDED")
        self.assertIn("correction", self.email.auto_response_text.lower())

    def test_skips_escalated_emails(self):
        self.email.escalated = True
        self.email.response_status = "ESCALATED"
        self.email.save()

        auto_respond(self.email)
        self.email.refresh_from_db()
        self.assertEqual(self.email.response_status, "ESCALATED")

    def test_resolves_irrelevant_emails(self):
        self.email.classification = "IRRELEVANT"
        self.email.save()

        auto_respond(self.email)
        self.email.refresh_from_db()
        self.assertEqual(self.email.response_status, "RESOLVED")

    def test_skips_already_responded(self):
        self.email.response_status = "AUTO_RESPONDED"
        self.email.save()

        auto_respond(self.email)
        # Should not change anything — still AUTO_RESPONDED

    def test_response_for_tip(self):
        self.email.classification = "TIP"
        self.email.save()

        auto_respond(self.email)
        self.email.refresh_from_db()
        self.assertEqual(self.email.response_status, "AUTO_RESPONDED")
        self.assertIn("tip", self.email.auto_response_text.lower())

    def test_response_for_praise(self):
        self.email.classification = "PRAISE"
        self.email.save()

        auto_respond(self.email)
        self.email.refresh_from_db()
        self.assertEqual(self.email.response_status, "AUTO_RESPONDED")

    @patch("feedback.services.responder.requests.post")
    @patch.dict("os.environ", {"BREVO_API_KEY": "test-key"})
    def test_sends_via_brevo_when_api_key_set(self, mock_post):
        mock_post.return_value = Mock(
            status_code=201, json=lambda: {"messageId": "resp_001"}
        )

        auto_respond(self.email)
        self.email.refresh_from_db()

        self.assertEqual(self.email.response_status, "AUTO_RESPONDED")
        mock_post.assert_called_once()
        payload = mock_post.call_args[1]["json"]
        self.assertEqual(payload["sender"]["email"], "feedback@tamilschool.org")
        self.assertIn("Re:", payload["subject"])
