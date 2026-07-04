"""Sprint 32 test-debt catch-up: pending_moderation_count scoping.

The UserMenu badge (Sprint 32) uses `UserProfileSerializer.
pending_moderation_count`. Requires per-role scoping:

- SUPERADMIN / MODERATOR: see all pending suggestions globally.
- Bound school admin: see only their school's pending queue.
- Plain USER: always 0.
"""

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from community.models import Suggestion
from schools.models import Constituency, School


class PendingModerationCountScopingTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.constituency = Constituency.objects.create(
            code="P001", name="C", state="Selangor",
        )
        self.school_a = School.objects.create(
            moe_code="ABC1234", name="A", short_name="A",
            constituency=self.constituency, state="Selangor",
        )
        self.school_b = School.objects.create(
            moe_code="XYZ9999", name="B", short_name="B",
            constituency=self.constituency, state="Selangor",
        )

        self.regular = UserProfile.objects.create(
            user=User.objects.create_user("reg"),
            google_id="g-reg", display_name="Reg",
        )
        self.moderator = UserProfile.objects.create(
            user=User.objects.create_user("mod"),
            google_id="g-mod", display_name="Mod", role="MODERATOR",
        )
        self.superadmin = UserProfile.objects.create(
            user=User.objects.create_user("super"),
            google_id="g-super", display_name="Super", role="SUPERADMIN",
        )
        self.bound_admin_a = UserProfile.objects.create(
            user=User.objects.create_user("bounda"),
            google_id="g-ba", display_name="BoundA",
            admin_school=self.school_a,
        )

        # 3 PENDING on school A, 2 PENDING on school B, plus 1 APPROVED
        # (which must not count).
        author = UserProfile.objects.create(
            user=User.objects.create_user("auth"),
            google_id="g-auth", display_name="Auth",
        )
        for _ in range(3):
            Suggestion.objects.create(
                school=self.school_a, user=author,
                type=Suggestion.Type.NOTE, status=Suggestion.Status.PENDING,
            )
        for _ in range(2):
            Suggestion.objects.create(
                school=self.school_b, user=author,
                type=Suggestion.Type.NOTE, status=Suggestion.Status.PENDING,
            )
        Suggestion.objects.create(
            school=self.school_a, user=author,
            type=Suggestion.Type.NOTE, status=Suggestion.Status.APPROVED,
        )

    def _me(self, profile):
        session = self.client.session
        session["user_profile_id"] = profile.pk
        session.save()
        return self.client.get("/api/v1/auth/me/").json()

    def test_superadmin_sees_global_count(self):
        self.assertEqual(self._me(self.superadmin)["pending_moderation_count"], 5)

    def test_moderator_sees_global_count(self):
        self.assertEqual(self._me(self.moderator)["pending_moderation_count"], 5)

    def test_bound_school_admin_sees_only_own_school_count(self):
        self.assertEqual(
            self._me(self.bound_admin_a)["pending_moderation_count"], 3,
        )

    def test_regular_user_sees_zero(self):
        self.assertEqual(self._me(self.regular)["pending_moderation_count"], 0)
