from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from community.models import Suggestion
from schools.models import Constituency, School


class SuggestionAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.constituency = Constituency.objects.create(
            code="P001", name="Test", state="Selangor",
        )
        self.school = School.objects.create(
            moe_code="ABC1234",
            name="SJK(T) Test",
            short_name="SJK(T) Test",
            constituency=self.constituency,
            state="Selangor",
            phone="03-1234567",
        )
        self.user = User.objects.create_user("testuser")
        self.profile = UserProfile.objects.create(
            user=self.user,
            google_id="google-123",
            display_name="Test User",
        )

    def _auth(self, profile=None):
        p = profile or self.profile
        session = self.client.session
        session["user_profile_id"] = p.pk
        session.save()

    def test_create_data_correction(self):
        self._auth()
        resp = self.client.post(
            "/api/v1/schools/ABC1234/suggestions/",
            {"type": "DATA_CORRECTION", "field_name": "phone", "suggested_value": "03-9999999"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["current_value"], "03-1234567")
        self.assertEqual(resp.data["suggested_value"], "03-9999999")

    def test_create_note(self):
        self._auth()
        resp = self.client.post(
            "/api/v1/schools/ABC1234/suggestions/",
            {"type": "NOTE", "note": "School has relocated to a new building"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)

    def test_blocked_for_own_school(self):
        self.profile.admin_school = self.school
        self.profile.save()
        self._auth()
        resp = self.client.post(
            "/api/v1/schools/ABC1234/suggestions/",
            {"type": "NOTE", "note": "test"},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_rejects_non_suggestible_field(self):
        self._auth()
        resp = self.client.post(
            "/api/v1/schools/ABC1234/suggestions/",
            {"type": "DATA_CORRECTION", "field_name": "enrolment", "suggested_value": "500"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_list_suggestions(self):
        self._auth()
        Suggestion.objects.create(
            school=self.school, user=self.profile, type="NOTE", note="Test note",
        )
        resp = self.client.get("/api/v1/schools/ABC1234/suggestions/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)

    def test_unauthenticated_rejected(self):
        resp = self.client.post(
            "/api/v1/schools/ABC1234/suggestions/",
            {"type": "NOTE", "note": "test"},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)
