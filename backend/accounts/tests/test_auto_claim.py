"""Tests for _maybe_auto_claim: binding admin_school when signing in with @moe.edu.my."""

from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from schools.models import Constituency, School


class AutoClaimTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/auth/google/"
        self.constituency = Constituency.objects.create(
            code="P004", name="Langkawi", state="Kedah",
        )
        self.school = School.objects.create(
            moe_code="KBD6019",
            name="SJK(T) Ladang Sungai Raya",
            short_name="SJK(T) Ladang Sungai Raya",
            constituency=self.constituency,
            state="Kedah",
        )

    def _auth_with(self, sub, email, name="Test"):
        with patch("accounts.api.views.verify_google_token") as mock:
            mock.return_value = {
                "sub": sub, "email": email, "name": name, "picture": "",
            }
            return self.client.post(self.url, {"id_token": "fake-token"})

    def test_moe_email_claims_matching_school(self):
        resp = self._auth_with("g-1", "kbd6019@moe.edu.my")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["admin_school"]["moe_code"], "KBD6019")

        profile = UserProfile.objects.get(google_id="g-1")
        self.assertEqual(profile.admin_school, self.school)

        self.school.refresh_from_db()
        self.assertIsNotNone(self.school.claimed_at)

    def test_moe_email_uppercase_still_claims(self):
        resp = self._auth_with("g-2", "KBD6019@moe.edu.my")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["admin_school"]["moe_code"], "KBD6019")

    def test_non_moe_email_does_not_claim(self):
        resp = self._auth_with("g-3", "user@gmail.com")
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.data["admin_school"])

        self.school.refresh_from_db()
        self.assertIsNone(self.school.claimed_at)

    def test_moe_email_with_no_matching_school_does_not_claim(self):
        resp = self._auth_with("g-4", "xyz9999@moe.edu.my")
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.data["admin_school"])

    def test_school_already_claimed_by_another_user_does_not_overwrite(self):
        other_user = User.objects.create_user("other", "other@moe.edu.my")
        UserProfile.objects.create(
            user=other_user, google_id="g-other",
            display_name="Other", admin_school=self.school,
        )
        # Second user tries to claim the same school via another @moe.edu.my email
        resp = self._auth_with("g-5", "kbd6019@moe.edu.my")
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.data["admin_school"])

        # Original claim still intact
        claimed_by = UserProfile.objects.get(google_id="g-other")
        self.assertEqual(claimed_by.admin_school, self.school)

    def test_claimed_at_only_set_once(self):
        """If school is re-claimed later (shouldn't happen, but just in case),
        claimed_at retains the original value."""
        from django.utils import timezone
        from datetime import timedelta

        past = timezone.now() - timedelta(days=10)
        self.school.claimed_at = past
        self.school.save()

        user = User.objects.create_user("u1", "kbd6019@moe.edu.my")
        profile = UserProfile.objects.create(
            user=user, google_id="g-6", display_name="U1",
        )

        # Signing in a profile that already has admin_school unset; simulate manual reset
        profile.admin_school = None
        profile.save()
        # Should re-bind but NOT overwrite claimed_at
        resp = self._auth_with("g-6", "kbd6019@moe.edu.my")
        self.assertEqual(resp.status_code, 200)

        self.school.refresh_from_db()
        # claimed_at unchanged
        self.assertEqual(self.school.claimed_at, past)

    def test_auto_claim_skipped_if_profile_already_has_school(self):
        other_school = School.objects.create(
            moe_code="KBD9999", name="Other School", short_name="Other",
            constituency=self.constituency, state="Kedah",
        )
        user = User.objects.create_user("u2", "kbd6019@moe.edu.my")
        UserProfile.objects.create(
            user=user, google_id="g-7", display_name="U2",
            admin_school=other_school,
        )
        resp = self._auth_with("g-7", "kbd6019@moe.edu.my")
        self.assertEqual(resp.status_code, 200)
        # admin_school stayed on other_school, not switched to KBD6019
        self.assertEqual(resp.data["admin_school"]["moe_code"], "KBD9999")
