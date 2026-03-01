from django.db import IntegrityError
from django.test import TestCase

from subscribers.models import Subscriber, SubscriptionPreference


class SubscriberModelTest(TestCase):
    def test_create_subscriber(self):
        sub = Subscriber.objects.create(email="test@example.com")
        self.assertEqual(sub.email, "test@example.com")
        self.assertTrue(sub.is_active)
        self.assertIsNotNone(sub.unsubscribe_token)
        self.assertIsNotNone(sub.subscribed_at)
        self.assertIsNone(sub.unsubscribed_at)

    def test_create_subscriber_with_all_fields(self):
        sub = Subscriber.objects.create(
            email="leader@tamilfoundation.org",
            name="Elan",
            organisation="Tamil Foundation",
        )
        self.assertEqual(sub.name, "Elan")
        self.assertEqual(sub.organisation, "Tamil Foundation")

    def test_email_unique(self):
        Subscriber.objects.create(email="test@example.com")
        with self.assertRaises(IntegrityError):
            Subscriber.objects.create(email="test@example.com")

    def test_unsubscribe_token_unique(self):
        sub1 = Subscriber.objects.create(email="a@example.com")
        sub2 = Subscriber.objects.create(email="b@example.com")
        self.assertNotEqual(sub1.unsubscribe_token, sub2.unsubscribe_token)

    def test_str_active(self):
        sub = Subscriber.objects.create(email="test@example.com")
        self.assertEqual(str(sub), "test@example.com (active)")

    def test_str_unsubscribed(self):
        sub = Subscriber.objects.create(email="test@example.com", is_active=False)
        self.assertEqual(str(sub), "test@example.com (unsubscribed)")

    def test_default_ordering(self):
        """Ordering is -subscribed_at (most recent first)."""
        self.assertEqual(Subscriber._meta.ordering, ["-subscribed_at"])

    def test_blank_name_and_org(self):
        sub = Subscriber.objects.create(email="test@example.com")
        self.assertEqual(sub.name, "")
        self.assertEqual(sub.organisation, "")


class SubscriptionPreferenceModelTest(TestCase):
    def setUp(self):
        self.subscriber = Subscriber.objects.create(email="test@example.com")

    def test_create_preference(self):
        pref = SubscriptionPreference.objects.create(
            subscriber=self.subscriber,
            category=SubscriptionPreference.PARLIAMENT_WATCH,
        )
        self.assertTrue(pref.is_enabled)
        self.assertEqual(pref.category, "PARLIAMENT_WATCH")

    def test_unique_together(self):
        SubscriptionPreference.objects.create(
            subscriber=self.subscriber,
            category=SubscriptionPreference.PARLIAMENT_WATCH,
        )
        with self.assertRaises(IntegrityError):
            SubscriptionPreference.objects.create(
                subscriber=self.subscriber,
                category=SubscriptionPreference.PARLIAMENT_WATCH,
            )

    def test_all_categories(self):
        categories = [c[0] for c in SubscriptionPreference.CATEGORY_CHOICES]
        self.assertEqual(len(categories), 3)
        self.assertIn("PARLIAMENT_WATCH", categories)
        self.assertIn("NEWS_WATCH", categories)
        self.assertIn("MONTHLY_BLAST", categories)

    def test_str_enabled(self):
        pref = SubscriptionPreference.objects.create(
            subscriber=self.subscriber,
            category=SubscriptionPreference.PARLIAMENT_WATCH,
            is_enabled=True,
        )
        self.assertIn("Parliament Watch", str(pref))
        self.assertIn("on", str(pref))

    def test_str_disabled(self):
        pref = SubscriptionPreference.objects.create(
            subscriber=self.subscriber,
            category=SubscriptionPreference.NEWS_WATCH,
            is_enabled=False,
        )
        self.assertIn("News Watch", str(pref))
        self.assertIn("off", str(pref))

    def test_cascade_delete(self):
        SubscriptionPreference.objects.create(
            subscriber=self.subscriber,
            category=SubscriptionPreference.MONTHLY_BLAST,
        )
        self.assertEqual(SubscriptionPreference.objects.count(), 1)
        self.subscriber.delete()
        self.assertEqual(SubscriptionPreference.objects.count(), 0)

    def test_ordering(self):
        SubscriptionPreference.objects.create(
            subscriber=self.subscriber,
            category=SubscriptionPreference.NEWS_WATCH,
        )
        SubscriptionPreference.objects.create(
            subscriber=self.subscriber,
            category=SubscriptionPreference.MONTHLY_BLAST,
        )
        prefs = list(self.subscriber.preferences.values_list("category", flat=True))
        # Alphabetical ordering
        self.assertEqual(prefs[0], "MONTHLY_BLAST")
        self.assertEqual(prefs[1], "NEWS_WATCH")
