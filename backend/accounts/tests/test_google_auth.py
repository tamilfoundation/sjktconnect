from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from accounts.models import UserProfile
from accounts.services.google import verify_google_token


# Sprint 18 close (TD-11): direct tests of verify_google_token covering
# the failure branches that brought line coverage from 25% to ~90%+.
# The existing GoogleAuthEndpointTests below mock verify_google_token
# itself, so they exercise the API view but not the verifier.
@patch("accounts.services.google._get_client_ids", return_value=["client-id-123"])
class VerifyGoogleTokenTests(TestCase):
    """Failure-branch coverage for verify_google_token."""

    @patch("accounts.services.google.id_token.verify_oauth2_token")
    def test_happy_path_returns_user_dict(self, mock_verify, _client_ids):
        mock_verify.return_value = {
            "iss": "https://accounts.google.com",
            "aud": "client-id-123",
            "sub": "google-sub-1",
            "email": "user@example.com",
            "name": "Test User",
            "picture": "https://lh3.googleusercontent.com/a.jpg",
        }
        result = verify_google_token("fake-token")
        self.assertEqual(result["sub"], "google-sub-1")
        self.assertEqual(result["email"], "user@example.com")
        self.assertEqual(result["name"], "Test User")
        self.assertEqual(result["picture"], "https://lh3.googleusercontent.com/a.jpg")

    @patch("accounts.services.google.id_token.verify_oauth2_token")
    def test_alt_issuer_form_accepted(self, mock_verify, _client_ids):
        # The verifier accepts both "accounts.google.com" and
        # "https://accounts.google.com" — Google docs list both as valid.
        mock_verify.return_value = {
            "iss": "accounts.google.com",
            "aud": "client-id-123",
            "sub": "google-sub-1",
        }
        self.assertIsNotNone(verify_google_token("fake-token"))

    @patch("accounts.services.google.id_token.verify_oauth2_token")
    def test_bad_issuer_returns_none(self, mock_verify, _client_ids):
        # Token forged by an attacker pretending to be Google.
        mock_verify.return_value = {
            "iss": "https://attacker.example.com",
            "aud": "client-id-123",
            "sub": "google-sub-1",
        }
        self.assertIsNone(verify_google_token("fake-token"))

    @patch("accounts.services.google.id_token.verify_oauth2_token")
    def test_bad_audience_returns_none(self, mock_verify, _client_ids):
        # Token meant for a different OAuth client (could be any other
        # Google-authenticated app on the internet).
        mock_verify.return_value = {
            "iss": "https://accounts.google.com",
            "aud": "some-other-client-id",
            "sub": "google-sub-1",
        }
        self.assertIsNone(verify_google_token("fake-token"))

    @patch("accounts.services.google.id_token.verify_oauth2_token")
    def test_verify_raises_returns_none(self, mock_verify, _client_ids):
        # Expired/malformed/signature-mismatch tokens raise from the
        # google-auth library. We catch broadly so the request gets a
        # clean 401 instead of a 500.
        mock_verify.side_effect = ValueError("Token expired")
        self.assertIsNone(verify_google_token("fake-token"))

    @patch("accounts.services.google.id_token.verify_oauth2_token")
    def test_network_error_returns_none(self, mock_verify, _client_ids):
        # google_requests.Request() makes a network call to fetch
        # Google's signing certs; treat the failure the same way.
        mock_verify.side_effect = ConnectionError("Network unreachable")
        self.assertIsNone(verify_google_token("fake-token"))


@patch("accounts.services.google._get_client_ids", return_value=[])
class VerifyGoogleTokenNoConfigTests(TestCase):
    """Server-config failure mode — no GOOGLE_OAUTH_CLIENT_ID set."""

    def test_no_client_id_returns_none(self, _client_ids):
        # Should never call verify_oauth2_token because the early-return
        # fires first. If this test ever fails to early-return, the
        # token would be validated against an empty audience list and
        # silently rejected — still safe but harder to debug.
        result = verify_google_token("any-token")
        self.assertIsNone(result)


class GoogleAuthEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/auth/google/"

    @patch("accounts.api.views.verify_google_token")
    def test_new_user_created(self, mock_verify):
        mock_verify.return_value = {
            "sub": "google-abc-123",
            "email": "user@gmail.com",
            "name": "Test User",
            "picture": "https://lh3.googleusercontent.com/photo.jpg",
        }
        response = self.client.post(self.url, {"id_token": "fake-token"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["google_id"], "google-abc-123")
        self.assertEqual(response.data["display_name"], "Test User")
        self.assertEqual(response.data["role"], "USER")
        self.assertEqual(response.data["points"], 0)
        self.assertIsNone(response.data["admin_school"])
        # Django User also created
        self.assertTrue(User.objects.filter(email="user@gmail.com").exists())
        # Profile linked
        profile = UserProfile.objects.get(google_id="google-abc-123")
        self.assertEqual(profile.user.email, "user@gmail.com")

    @patch("accounts.api.views.verify_google_token")
    def test_existing_user_returns_profile(self, mock_verify):
        mock_verify.return_value = {
            "sub": "google-abc-123",
            "email": "user@gmail.com",
            "name": "Updated Name",
            "picture": "https://lh3.googleusercontent.com/new.jpg",
        }
        # First login
        self.client.post(self.url, {"id_token": "fake-token"})
        # Second login
        response = self.client.post(self.url, {"id_token": "fake-token"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(UserProfile.objects.count(), 1)
        # Name/avatar updated
        profile = UserProfile.objects.get(google_id="google-abc-123")
        self.assertEqual(profile.display_name, "Updated Name")

    @patch("accounts.api.views.verify_google_token")
    def test_invalid_token_returns_401(self, mock_verify):
        mock_verify.return_value = None
        response = self.client.post(self.url, {"id_token": "bad-token"})
        self.assertEqual(response.status_code, 401)

    def test_missing_token_returns_400(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 400)

    @patch("accounts.api.views.verify_google_token")
    def test_session_set_on_success(self, mock_verify):
        mock_verify.return_value = {
            "sub": "google-abc-123",
            "email": "user@gmail.com",
            "name": "Test",
            "picture": "",
        }
        response = self.client.post(self.url, {"id_token": "fake-token"})
        self.assertEqual(response.status_code, 200)
        # Session should contain user_profile_id
        self.assertIn("user_profile_id", self.client.session)
