import uuid

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from subscribers.models import Subscriber, SubscriptionPreference
from subscribers.services.subscriber_service import subscribe


class SubscribeAPITest(TestCase):
    def setUp(self):
        # Sprint 22: SubscribeView is throttled at 5/hour per IP. DRF
        # stores throttle counts in the default cache, which persists
        # across tests in the same process. Clear before each test so
        # the rate limit doesn't fire on the 6th test in this class.
        cache.clear()
        self.client = APIClient()
        self.url = "/api/v1/subscribers/subscribe/"

    def test_subscribe_success(self):
        response = self.client.post(
            self.url,
            {"email": "test@gmail.com", "name": "Test", "organisation": "TestOrg"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["email"], "test@gmail.com")
        self.assertEqual(response.data["name"], "Test")
        self.assertTrue(response.data["is_active"])
        self.assertIn("preferences", response.data)
        self.assertEqual(len(response.data["preferences"]), 3)
        # All preferences enabled by default
        for enabled in response.data["preferences"].values():
            self.assertTrue(enabled)

    def test_subscribe_email_only(self):
        response = self.client.post(
            self.url, {"email": "minimal@gmail.com"}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["email"], "minimal@gmail.com")
        self.assertEqual(response.data["name"], "")

    def test_subscribe_duplicate_returns_200(self):
        self.client.post(self.url, {"email": "test@gmail.com"}, format="json")
        response = self.client.post(
            self.url, {"email": "test@gmail.com"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Subscriber.objects.count(), 1)

    def test_subscribe_invalid_email(self):
        response = self.client.post(
            self.url, {"email": "not-an-email"}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_subscribe_rate_limit_enforced_at_5_per_hour(self):
        """Sprint 22: 5/hour per anonymous IP. 6th attempt → 429."""
        for i in range(5):
            response = self.client.post(
                self.url,
                {"email": f"user{i}@gmail.com"},
                format="json",
            )
            self.assertIn(response.status_code, (200, 201), msg=f"attempt {i+1}")
        response = self.client.post(
            self.url, {"email": "user5@gmail.com"}, format="json"
        )
        self.assertEqual(response.status_code, 429)

    def test_subscribe_blocklisted_domain_returns_400(self):
        """Sprint 22: example.com, test.com, mailinator etc.
        rejected at validation. Bots flooding the form with
        test@example.com → no DB row, no Brevo API call."""
        for blocked in ("test@example.com", "foo@mailinator.com", "x@my.invalid"):
            response = self.client.post(
                self.url, {"email": blocked}, format="json"
            )
            self.assertEqual(
                response.status_code, 400,
                msg=f"expected 400 for {blocked}, got {response.status_code}",
            )
        self.assertEqual(Subscriber.objects.count(), 0)

    def test_subscribe_missing_email(self):
        response = self.client.post(
            self.url, {"name": "No Email"}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_subscribe_reactivates_unsubscribed(self):
        # Subscribe, then unsubscribe
        sub, _ = subscribe("test@gmail.com")
        self.client.get(f"/api/v1/subscribers/unsubscribe/{sub.unsubscribe_token}/")

        # Re-subscribe
        response = self.client.post(
            self.url, {"email": "test@gmail.com"}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["is_active"])


class UnsubscribeAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_unsubscribe_valid(self):
        sub, _ = subscribe("test@gmail.com")
        response = self.client.get(
            f"/api/v1/subscribers/unsubscribe/{sub.unsubscribe_token}/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "test@gmail.com")
        self.assertIn("unsubscribed", response.data["detail"])

    def test_unsubscribe_invalid_token(self):
        response = self.client.get(
            f"/api/v1/subscribers/unsubscribe/{uuid.uuid4()}/"
        )
        self.assertEqual(response.status_code, 404)

    def test_unsubscribe_idempotent(self):
        sub, _ = subscribe("test@gmail.com")
        url = f"/api/v1/subscribers/unsubscribe/{sub.unsubscribe_token}/"
        self.client.get(url)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_unsubscribe_deactivates_subscriber(self):
        sub, _ = subscribe("test@gmail.com")
        self.client.get(
            f"/api/v1/subscribers/unsubscribe/{sub.unsubscribe_token}/"
        )
        sub.refresh_from_db()
        self.assertFalse(sub.is_active)
        self.assertIsNotNone(sub.unsubscribed_at)


class PreferencesAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.subscriber, _ = subscribe("test@gmail.com")
        self.url = f"/api/v1/subscribers/preferences/{self.subscriber.unsubscribe_token}/"

    def test_get_preferences(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "test@gmail.com")
        self.assertIn("preferences", response.data)
        prefs = response.data["preferences"]
        self.assertTrue(prefs["PARLIAMENT_WATCH"])
        self.assertTrue(prefs["NEWS_WATCH"])
        self.assertTrue(prefs["MONTHLY_BLAST"])

    def test_get_preferences_invalid_token(self):
        response = self.client.get(
            f"/api/v1/subscribers/preferences/{uuid.uuid4()}/"
        )
        self.assertEqual(response.status_code, 404)

    def test_update_single_preference(self):
        response = self.client.put(
            self.url, {"NEWS_WATCH": False}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["preferences"]["NEWS_WATCH"])
        self.assertTrue(response.data["preferences"]["PARLIAMENT_WATCH"])
        self.assertTrue(response.data["preferences"]["MONTHLY_BLAST"])

    def test_update_multiple_preferences(self):
        response = self.client.put(
            self.url,
            {"NEWS_WATCH": False, "MONTHLY_BLAST": False},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["preferences"]["NEWS_WATCH"])
        self.assertFalse(response.data["preferences"]["MONTHLY_BLAST"])
        self.assertTrue(response.data["preferences"]["PARLIAMENT_WATCH"])

    def test_update_preferences_invalid_token(self):
        response = self.client.put(
            f"/api/v1/subscribers/preferences/{uuid.uuid4()}/",
            {"NEWS_WATCH": False},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_update_empty_body(self):
        response = self.client.put(self.url, {}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_update_toggle_back(self):
        self.client.put(self.url, {"NEWS_WATCH": False}, format="json")
        response = self.client.put(
            self.url, {"NEWS_WATCH": True}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["preferences"]["NEWS_WATCH"])

    def test_preferences_persist(self):
        self.client.put(self.url, {"NEWS_WATCH": False}, format="json")
        response = self.client.get(self.url)
        self.assertFalse(response.data["preferences"]["NEWS_WATCH"])
