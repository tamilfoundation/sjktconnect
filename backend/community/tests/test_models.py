from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from community.models import Suggestion
from schools.models import Constituency, School


class SuggestionModelTest(TestCase):
    def setUp(self):
        self.constituency = Constituency.objects.create(
            code="P001", name="Test", state="Selangor"
        )
        self.school = School.objects.create(
            moe_code="ABC1234",
            name="SJK(T) Test",
            short_name="SJK(T) Test",
            constituency=self.constituency,
            state="Selangor",
        )
        self.user = User.objects.create_user("testuser")
        self.profile = UserProfile.objects.create(
            user=self.user,
            google_id="google-123",
            display_name="Test User",
        )

    def test_create_data_correction(self):
        s = Suggestion.objects.create(
            school=self.school,
            user=self.profile,
            type=Suggestion.Type.DATA_CORRECTION,
            field_name="phone",
            current_value="03-1234567",
            suggested_value="03-7654321",
        )
        self.assertEqual(s.status, Suggestion.Status.PENDING)
        self.assertEqual(str(s), "ABC1234 — Data Correction (Pending)")

    def test_create_photo_upload(self):
        from django.core.files.base import ContentFile
        from community.tests.fixtures import valid_png_bytes

        s = Suggestion.objects.create(
            school=self.school,
            user=self.profile,
            type=Suggestion.Type.PHOTO_UPLOAD,
            phash="abc123def456",
        )
        s.pending_image.save("test.png", ContentFile(valid_png_bytes()), save=True)
        self.assertEqual(s.type, Suggestion.Type.PHOTO_UPLOAD)
        self.assertTrue(s.pending_image)
        self.assertEqual(s.phash, "abc123def456")

    def test_create_note(self):
        s = Suggestion.objects.create(
            school=self.school,
            user=self.profile,
            type=Suggestion.Type.NOTE,
            note="This school has moved to a new building",
        )
        self.assertEqual(s.type, Suggestion.Type.NOTE)

    def test_points_map(self):
        self.assertEqual(Suggestion.POINTS_MAP["DATA_CORRECTION"], 2)
        self.assertEqual(Suggestion.POINTS_MAP["PHOTO_UPLOAD"], 3)
        self.assertEqual(Suggestion.POINTS_MAP["NOTE"], 1)

    def test_suggestible_fields_list(self):
        self.assertIn("phone", Suggestion.SUGGESTIBLE_FIELDS)
        self.assertNotIn("enrolment", Suggestion.SUGGESTIBLE_FIELDS)
        self.assertNotIn("email", Suggestion.SUGGESTIBLE_FIELDS)
