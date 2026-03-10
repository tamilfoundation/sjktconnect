from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from accounts.models import UserProfile


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
