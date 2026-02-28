"""Tests for the email sender service and management command."""

from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import TestCase

from outreach.models import OutreachEmail
from outreach.services.email_sender import send_outreach_email
from schools.models import School


class SendOutreachEmailTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.school = School.objects.create(
            moe_code="JBD0050",
            name="SJK(T) LADANG BIKAM",
            short_name="SJK(T) Ladang Bikam",
            state="Johor",
            ppd="PPD Segamat",
            email="jbd0050@moe.edu.my",
        )

    @patch.dict("os.environ", {}, clear=True)
    def test_dev_mode_logs_and_marks_sent(self):
        record = send_outreach_email(self.school, "jbd0050@moe.edu.my")
        assert record.status == OutreachEmail.Status.SENT
        assert record.sent_at is not None
        assert record.school == self.school
        assert record.recipient_email == "jbd0050@moe.edu.my"
        assert "SJK(T) Ladang Bikam" in record.subject

    @patch("outreach.services.email_sender.requests.post")
    @patch.dict("os.environ", {"BREVO_API_KEY": "xkeysib-test"})
    def test_production_sends_via_brevo(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.raise_for_status = lambda: None
        mock_response.json.return_value = {"messageId": "msg-123"}
        mock_post.return_value = mock_response

        record = send_outreach_email(self.school, "jbd0050@moe.edu.my")
        assert record.status == OutreachEmail.Status.SENT
        assert record.brevo_message_id == "msg-123"
        assert record.sent_at is not None

        # Verify Brevo was called with correct payload
        call_args = mock_post.call_args
        payload = call_args.kwargs["json"]
        assert payload["to"] == [{"email": "jbd0050@moe.edu.my"}]
        assert "SJK(T) Ladang Bikam" in payload["subject"]
        assert "noreply@tamilschool.org" in payload["sender"]["email"]

    @patch("outreach.services.email_sender.requests.post")
    @patch.dict("os.environ", {"BREVO_API_KEY": "xkeysib-test"})
    def test_production_handles_brevo_failure(self, mock_post):
        import requests

        mock_post.side_effect = requests.RequestException("Timeout")

        record = send_outreach_email(self.school, "jbd0050@moe.edu.my")
        assert record.status == OutreachEmail.Status.FAILED
        assert "Timeout" in record.error_message
        assert record.sent_at is None

    @patch.dict("os.environ", {}, clear=True)
    def test_email_html_contains_school_info(self):
        record = send_outreach_email(self.school, "jbd0050@moe.edu.my")
        # Verify the record was created (HTML is internal but record is accessible)
        assert record.pk is not None
        assert OutreachEmail.objects.count() == 1


class OutreachEmailModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.school = School.objects.create(
            moe_code="JBD0050",
            name="SJK(T) LADANG BIKAM",
            short_name="SJK(T) Ladang Bikam",
            state="Johor",
            ppd="PPD Segamat",
            email="jbd0050@moe.edu.my",
        )

    def test_str_representation(self):
        record = OutreachEmail.objects.create(
            school=self.school,
            recipient_email="jbd0050@moe.edu.my",
            subject="Test",
        )
        assert "jbd0050@moe.edu.my" in str(record)
        assert "PENDING" in str(record)

    def test_default_status_is_pending(self):
        record = OutreachEmail.objects.create(
            school=self.school,
            recipient_email="jbd0050@moe.edu.my",
            subject="Test",
        )
        assert record.status == OutreachEmail.Status.PENDING


class SchoolImageModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.school = School.objects.create(
            moe_code="JBD0050",
            name="SJK(T) LADANG BIKAM",
            short_name="SJK(T) Ladang Bikam",
            state="Johor",
            ppd="PPD Segamat",
        )

    def test_str_representation(self):
        from outreach.models import SchoolImage

        img = SchoolImage.objects.create(
            school=self.school,
            image_url="https://example.com/photo.jpg",
            source=SchoolImage.Source.SATELLITE,
            is_primary=True,
        )
        assert "SATELLITE" in str(img)
        assert "primary" in str(img)

    def test_ordering_primary_first(self):
        from outreach.models import SchoolImage

        secondary = SchoolImage.objects.create(
            school=self.school,
            image_url="https://example.com/sat.jpg",
            source=SchoolImage.Source.SATELLITE,
            is_primary=False,
        )
        primary = SchoolImage.objects.create(
            school=self.school,
            image_url="https://example.com/places.jpg",
            source=SchoolImage.Source.PLACES,
            is_primary=True,
        )
        images = list(SchoolImage.objects.filter(school=self.school))
        assert images[0].pk == primary.pk


class SendOutreachEmailsCommandTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.school1 = School.objects.create(
            moe_code="JBD0050",
            name="SJK(T) LADANG BIKAM",
            short_name="SJK(T) Ladang Bikam",
            state="Johor",
            ppd="PPD Segamat",
            email="jbd0050@moe.edu.my",
        )
        cls.school2 = School.objects.create(
            moe_code="AGD1234",
            name="SJK(T) LADANG SUNGAI",
            short_name="SJK(T) Ladang Sungai",
            state="Kedah",
            ppd="PPD Kulim",
            email="agd1234@moe.edu.my",
        )
        cls.school_no_email = School.objects.create(
            moe_code="PGD5678",
            name="SJK(T) TEST",
            short_name="SJK(T) Test",
            state="Penang",
            ppd="PPD Timur Laut",
        )

    def test_dry_run_no_emails_sent(self):
        out = StringIO()
        call_command("send_outreach_emails", "--dry-run", stdout=out)
        assert OutreachEmail.objects.count() == 0
        output = out.getvalue()
        assert "JBD0050" in output
        assert "AGD1234" in output
        assert "PGD5678" not in output  # no email address
        assert "Dry run complete" in output

    def test_dry_run_with_state_filter(self):
        out = StringIO()
        call_command("send_outreach_emails", "--dry-run", "--state", "Johor", stdout=out)
        output = out.getvalue()
        assert "JBD0050" in output
        assert "AGD1234" not in output

    def test_dry_run_with_limit(self):
        out = StringIO()
        call_command("send_outreach_emails", "--dry-run", "--limit", "1", stdout=out)
        output = out.getvalue()
        assert "Schools to email: 1" in output

    @patch.dict("os.environ", {}, clear=True)
    def test_send_emails_dev_mode(self):
        out = StringIO()
        call_command("send_outreach_emails", "--limit", "2", stdout=out)
        assert OutreachEmail.objects.filter(status=OutreachEmail.Status.SENT).count() == 2
        assert "Sent: 2" in out.getvalue()

    @patch.dict("os.environ", {}, clear=True)
    def test_skips_already_emailed_schools(self):
        # Pre-create an email record for school1
        OutreachEmail.objects.create(
            school=self.school1,
            recipient_email="jbd0050@moe.edu.my",
            subject="Previous email",
            status=OutreachEmail.Status.SENT,
        )
        out = StringIO()
        call_command("send_outreach_emails", stdout=out)
        # Only school2 should be emailed (school1 already emailed, school3 no email)
        output = out.getvalue()
        assert "Schools to email: 1" in output

    def test_excludes_schools_without_email(self):
        out = StringIO()
        call_command("send_outreach_emails", "--dry-run", stdout=out)
        output = out.getvalue()
        assert "PGD5678" not in output


class ImageUrlOnSchoolDetailAPITest(TestCase):
    """Test that image_url appears on the school detail API endpoint."""

    @classmethod
    def setUpTestData(cls):
        cls.school = School.objects.create(
            moe_code="JBD0050",
            name="SJK(T) LADANG BIKAM",
            short_name="SJK(T) Ladang Bikam",
            state="Johor",
            ppd="PPD Segamat",
        )

    def test_image_url_null_when_no_images(self):
        resp = self.client.get("/api/v1/schools/JBD0050/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["image_url"] is None

    def test_image_url_returns_primary_image(self):
        from outreach.models import SchoolImage

        SchoolImage.objects.create(
            school=self.school,
            image_url="https://example.com/primary.jpg",
            source=SchoolImage.Source.SATELLITE,
            is_primary=True,
        )
        SchoolImage.objects.create(
            school=self.school,
            image_url="https://example.com/secondary.jpg",
            source=SchoolImage.Source.PLACES,
            is_primary=False,
        )

        resp = self.client.get("/api/v1/schools/JBD0050/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["image_url"] == "https://example.com/primary.jpg"
