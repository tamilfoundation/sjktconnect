from django.test import TestCase

from feedback.models import InboundEmail


class InboundEmailModelTest(TestCase):
    def test_create_inbound_email(self):
        email = InboundEmail.objects.create(
            gmail_message_id="msg_abc123",
            from_email="reader@example.com",
            from_name="A Reader",
            subject="Re: Parliament Watch — 1st Meeting 2026",
            body_text="Great analysis! But you got the school name wrong.",
            source_broadcast_type="PARLIAMENT_WATCH",
        )
        self.assertEqual(email.classification, "UNCLASSIFIED")
        self.assertEqual(email.response_status, "PENDING")
        self.assertFalse(email.escalated)

    def test_classification_choices(self):
        email = InboundEmail.objects.create(
            gmail_message_id="msg_def456",
            from_email="tipster@example.com",
            subject="Re: News Watch",
            body_text="There is a story you missed.",
            classification="TIP",
        )
        self.assertEqual(email.classification, "TIP")

    def test_unique_gmail_message_id(self):
        InboundEmail.objects.create(
            gmail_message_id="msg_unique",
            from_email="a@example.com",
            subject="Test",
            body_text="Test",
        )
        with self.assertRaises(Exception):
            InboundEmail.objects.create(
                gmail_message_id="msg_unique",
                from_email="b@example.com",
                subject="Test 2",
                body_text="Test 2",
            )

    def test_str_representation(self):
        email = InboundEmail.objects.create(
            gmail_message_id="msg_str",
            from_email="reader@example.com",
            subject="Re: Parliament Watch",
            body_text="Test",
        )
        self.assertIn("reader@example.com", str(email))
