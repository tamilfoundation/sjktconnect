from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from community.models import Suggestion
from community.services import approve_suggestion, reject_suggestion
from outreach.models import SchoolImage
from schools.models import Constituency, School


class ApprovalServiceTest(TestCase):
    def setUp(self):
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
        self.mod_user = User.objects.create_user("moduser")
        self.moderator = UserProfile.objects.create(
            user=self.mod_user,
            google_id="google-mod",
            display_name="Mod",
            role="MODERATOR",
        )

    def test_approve_data_correction_applies_change(self):
        s = Suggestion.objects.create(
            school=self.school,
            user=self.profile,
            type="DATA_CORRECTION",
            field_name="phone",
            current_value="03-1234567",
            suggested_value="03-9999999",
        )
        approve_suggestion(s, self.moderator)
        self.school.refresh_from_db()
        self.assertEqual(self.school.phone, "03-9999999")
        self.assertEqual(s.status, "APPROVED")
        self.assertEqual(s.points_awarded, 2)

    def test_approve_awards_points_to_user(self):
        s = Suggestion.objects.create(
            school=self.school,
            user=self.profile,
            type="NOTE",
            note="School relocated",
        )
        approve_suggestion(s, self.moderator)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.points, 1)

    def test_approve_photo_creates_school_image(self):
        from django.core.files.base import ContentFile
        from community.tests.fixtures import valid_png_bytes

        s = Suggestion.objects.create(
            school=self.school,
            user=self.profile,
            type="PHOTO_UPLOAD",
        )
        s.pending_image.save("test.png", ContentFile(valid_png_bytes()), save=True)
        approve_suggestion(s, self.moderator)
        self.assertEqual(SchoolImage.objects.filter(school=self.school).count(), 1)
        img = SchoolImage.objects.get(school=self.school)
        self.assertEqual(img.source, "COMMUNITY")
        self.assertEqual(img.uploaded_by, self.profile)
        self.assertTrue(img.image_file)
        s.refresh_from_db()
        self.assertFalse(s.pending_image)  # cleared after copy

    def test_reject_sets_reason(self):
        s = Suggestion.objects.create(
            school=self.school,
            user=self.profile,
            type="NOTE",
            note="test",
        )
        reject_suggestion(s, self.moderator, "Not relevant")
        self.assertEqual(s.status, "REJECTED")
        self.assertEqual(s.review_note, "Not relevant")
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.points, 0)

    def test_no_points_for_own_school(self):
        self.profile.admin_school = self.school
        self.profile.save()
        s = Suggestion.objects.create(
            school=self.school,
            user=self.profile,
            type="NOTE",
            note="test",
        )
        approve_suggestion(s, self.moderator)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.points, 0)
        self.assertEqual(s.points_awarded, 0)

    def test_service_skips_create_when_at_cap(self):
        """Defence in depth: service no-ops the create when 20 images exist.
        Cap is normally enforced upstream by the API view; this test guards
        the service-level fallback.
        """
        from django.core.files.base import ContentFile
        from community.tests.fixtures import valid_png_bytes

        for i in range(20):
            SchoolImage.objects.create(
                school=self.school,
                image_url=f"https://example.com/{i}.jpg",
                source="PLACES",
                position=i,
            )
        s = Suggestion.objects.create(
            school=self.school,
            user=self.profile,
            type="PHOTO_UPLOAD",
        )
        s.pending_image.save("test.png", ContentFile(valid_png_bytes()), save=True)
        approve_suggestion(s, self.moderator)
        self.assertEqual(SchoolImage.objects.filter(school=self.school).count(), 20)


class ModerationAPITest(TestCase):
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
        )
        self.user = User.objects.create_user("testuser")
        self.profile = UserProfile.objects.create(
            user=self.user,
            google_id="google-123",
            display_name="Test User",
        )
        self.mod_user = User.objects.create_user("moduser")
        self.moderator = UserProfile.objects.create(
            user=self.mod_user,
            google_id="google-mod",
            display_name="Mod",
            role="MODERATOR",
        )

    def _auth(self, profile):
        session = self.client.session
        session["user_profile_id"] = profile.pk
        session.save()

    def test_pending_queue_requires_moderator(self):
        self._auth(self.profile)
        resp = self.client.get("/api/v1/suggestions/pending/")
        self.assertEqual(resp.status_code, 403)

    def test_pending_queue_works_for_moderator(self):
        self._auth(self.moderator)
        Suggestion.objects.create(
            school=self.school, user=self.profile, type="NOTE", note="test",
        )
        resp = self.client.get("/api/v1/suggestions/pending/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)

    def test_approve_via_api(self):
        self._auth(self.moderator)
        s = Suggestion.objects.create(
            school=self.school, user=self.profile, type="NOTE", note="test",
        )
        resp = self.client.post(f"/api/v1/suggestions/{s.pk}/approve/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["status"], "APPROVED")

    def test_reject_via_api(self):
        self._auth(self.moderator)
        s = Suggestion.objects.create(
            school=self.school, user=self.profile, type="NOTE", note="test",
        )
        resp = self.client.post(
            f"/api/v1/suggestions/{s.pk}/reject/",
            {"reason": "Not useful"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["status"], "REJECTED")

    def test_regular_user_cannot_approve(self):
        self._auth(self.profile)
        s = Suggestion.objects.create(
            school=self.school, user=self.profile, type="NOTE", note="test",
        )
        resp = self.client.post(f"/api/v1/suggestions/{s.pk}/approve/")
        self.assertEqual(resp.status_code, 403)

    def test_school_admin_can_approve_own_school(self):
        admin_user = User.objects.create_user("schooladmin")
        admin_profile = UserProfile.objects.create(
            user=admin_user,
            google_id="google-admin",
            display_name="School Admin",
            admin_school=self.school,
        )
        self._auth(admin_profile)
        s = Suggestion.objects.create(
            school=self.school, user=self.profile, type="NOTE", note="test",
        )
        resp = self.client.post(f"/api/v1/suggestions/{s.pk}/approve/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["status"], "APPROVED")

    def test_school_admin_sees_only_own_school_in_queue(self):
        other_school = School.objects.create(
            moe_code="XYZ9999",
            name="SJK(T) Other",
            short_name="SJK(T) Other",
            constituency=self.constituency,
            state="Selangor",
        )
        admin_user = User.objects.create_user("schooladmin")
        admin_profile = UserProfile.objects.create(
            user=admin_user,
            google_id="google-admin",
            display_name="School Admin",
            admin_school=self.school,
        )
        Suggestion.objects.create(
            school=self.school, user=self.profile, type="NOTE", note="mine",
        )
        Suggestion.objects.create(
            school=other_school, user=self.profile, type="NOTE", note="other",
        )
        self._auth(admin_profile)
        resp = self.client.get("/api/v1/suggestions/pending/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)

    # Sprint 14: /api/v1/suggestions/<id>/image/ endpoint removed.
    # Bytes now live in Suggestion.pending_image (Supabase Storage URL exposed
    # via SuggestionListSerializer.pending_image_url to authorised viewers).
    # Coverage for the new flow lives in test_photo_upload.py.
