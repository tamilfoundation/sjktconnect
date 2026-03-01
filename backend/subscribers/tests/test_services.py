import uuid

from django.test import TestCase

from subscribers.models import Subscriber, SubscriptionPreference
from subscribers.services.subscriber_service import (
    get_preferences,
    subscribe,
    unsubscribe,
    update_preferences,
)


class SubscribeServiceTest(TestCase):
    def test_subscribe_new(self):
        sub, created = subscribe("test@example.com", "Test User", "Test Org")
        self.assertTrue(created)
        self.assertEqual(sub.email, "test@example.com")
        self.assertEqual(sub.name, "Test User")
        self.assertEqual(sub.organisation, "Test Org")
        self.assertTrue(sub.is_active)

    def test_subscribe_creates_default_preferences(self):
        sub, _ = subscribe("test@example.com")
        prefs = sub.preferences.all()
        self.assertEqual(prefs.count(), 3)
        for pref in prefs:
            self.assertTrue(pref.is_enabled)

    def test_subscribe_normalises_email(self):
        sub, _ = subscribe("  TEST@Example.COM  ")
        self.assertEqual(sub.email, "test@example.com")

    def test_subscribe_duplicate_idempotent(self):
        sub1, created1 = subscribe("test@example.com")
        sub2, created2 = subscribe("test@example.com")
        self.assertTrue(created1)
        self.assertFalse(created2)
        self.assertEqual(sub1.pk, sub2.pk)
        self.assertEqual(Subscriber.objects.count(), 1)

    def test_subscribe_duplicate_updates_name_if_blank(self):
        sub1, _ = subscribe("test@example.com")
        self.assertEqual(sub1.name, "")
        sub2, _ = subscribe("test@example.com", name="Test User")
        sub2.refresh_from_db()
        self.assertEqual(sub2.name, "Test User")

    def test_subscribe_duplicate_does_not_overwrite_name(self):
        sub1, _ = subscribe("test@example.com", name="Original")
        sub2, _ = subscribe("test@example.com", name="New Name")
        sub2.refresh_from_db()
        self.assertEqual(sub2.name, "Original")

    def test_subscribe_reactivates_unsubscribed(self):
        sub, _ = subscribe("test@example.com")
        unsubscribe(sub.unsubscribe_token)
        sub.refresh_from_db()
        self.assertFalse(sub.is_active)

        sub2, created = subscribe("test@example.com")
        self.assertTrue(created)
        self.assertTrue(sub2.is_active)
        self.assertIsNone(sub2.unsubscribed_at)


class UnsubscribeServiceTest(TestCase):
    def test_unsubscribe_valid_token(self):
        sub, _ = subscribe("test@example.com")
        result = unsubscribe(sub.unsubscribe_token)
        self.assertIsNotNone(result)
        self.assertFalse(result.is_active)
        self.assertIsNotNone(result.unsubscribed_at)

    def test_unsubscribe_invalid_token(self):
        result = unsubscribe(uuid.uuid4())
        self.assertIsNone(result)

    def test_unsubscribe_idempotent(self):
        sub, _ = subscribe("test@example.com")
        result1 = unsubscribe(sub.unsubscribe_token)
        result2 = unsubscribe(sub.unsubscribe_token)
        self.assertIsNotNone(result1)
        self.assertIsNotNone(result2)
        self.assertFalse(result2.is_active)


class GetPreferencesServiceTest(TestCase):
    def test_get_preferences_valid(self):
        sub, _ = subscribe("test@example.com")
        subscriber, prefs = get_preferences(sub.unsubscribe_token)
        self.assertIsNotNone(subscriber)
        self.assertEqual(prefs.count(), 3)

    def test_get_preferences_invalid_token(self):
        subscriber, prefs = get_preferences(uuid.uuid4())
        self.assertIsNone(subscriber)
        self.assertIsNone(prefs)

    def test_get_preferences_creates_missing(self):
        sub = Subscriber.objects.create(email="test@example.com")
        # No preferences created yet
        self.assertEqual(sub.preferences.count(), 0)
        subscriber, prefs = get_preferences(sub.unsubscribe_token)
        self.assertEqual(prefs.count(), 3)


class UpdatePreferencesServiceTest(TestCase):
    def test_update_single_preference(self):
        sub, _ = subscribe("test@example.com")
        subscriber, prefs = update_preferences(
            sub.unsubscribe_token,
            {"NEWS_WATCH": False},
        )
        self.assertIsNotNone(subscriber)
        news_pref = prefs.get(category="NEWS_WATCH")
        self.assertFalse(news_pref.is_enabled)
        # Others unchanged
        pw_pref = prefs.get(category="PARLIAMENT_WATCH")
        self.assertTrue(pw_pref.is_enabled)

    def test_update_multiple_preferences(self):
        sub, _ = subscribe("test@example.com")
        subscriber, prefs = update_preferences(
            sub.unsubscribe_token,
            {"NEWS_WATCH": False, "MONTHLY_BLAST": False},
        )
        self.assertFalse(prefs.get(category="NEWS_WATCH").is_enabled)
        self.assertFalse(prefs.get(category="MONTHLY_BLAST").is_enabled)
        self.assertTrue(prefs.get(category="PARLIAMENT_WATCH").is_enabled)

    def test_update_invalid_token(self):
        subscriber, prefs = update_preferences(
            uuid.uuid4(), {"NEWS_WATCH": False}
        )
        self.assertIsNone(subscriber)
        self.assertIsNone(prefs)

    def test_update_ignores_invalid_category(self):
        sub, _ = subscribe("test@example.com")
        subscriber, prefs = update_preferences(
            sub.unsubscribe_token,
            {"INVALID_CATEGORY": False, "NEWS_WATCH": False},
        )
        # Valid one applied
        self.assertFalse(prefs.get(category="NEWS_WATCH").is_enabled)
        # No crash from invalid category

    def test_update_toggle_back(self):
        sub, _ = subscribe("test@example.com")
        update_preferences(sub.unsubscribe_token, {"NEWS_WATCH": False})
        subscriber, prefs = update_preferences(
            sub.unsubscribe_token, {"NEWS_WATCH": True}
        )
        self.assertTrue(prefs.get(category="NEWS_WATCH").is_enabled)
