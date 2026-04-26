"""Sprint 15 hotfix — Django logout endpoint."""

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile


class LogoutEndpointTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user("u")
        self.profile = UserProfile.objects.create(
            user=self.user, google_id="g-1", display_name="U",
        )

    def _set_session(self):
        session = self.client.session
        session["user_profile_id"] = self.profile.pk
        session.save()

    def test_logout_flushes_session(self):
        self._set_session()
        # /me/ confirms the session is live
        me = self.client.get("/api/v1/auth/me/")
        self.assertEqual(me.status_code, 200)
        # Logout
        resp = self.client.post("/api/v1/auth/logout/")
        self.assertEqual(resp.status_code, 204)
        # /me/ now rejects (no session → IsProfileAuthenticated denies; DRF
        # returns 401 when no auth class authenticates).
        me_after = self.client.get("/api/v1/auth/me/")
        self.assertIn(me_after.status_code, (401, 403))

    def test_logout_idempotent_on_empty_session(self):
        # No session set — should still 204, not error
        resp = self.client.post("/api/v1/auth/logout/")
        self.assertEqual(resp.status_code, 204)
