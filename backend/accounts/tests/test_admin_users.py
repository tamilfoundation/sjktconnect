"""Tests for SUPERADMIN /dashboard/users endpoints and /me PATCH / /me/suggestions."""

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from community.models import Suggestion
from schools.models import Constituency, School


class _BaseCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.constituency = Constituency.objects.create(
            code="P001", name="Test", state="Selangor",
        )
        self.school_a = School.objects.create(
            moe_code="AAA0001", name="SJK(T) A", short_name="SJK(T) A",
            constituency=self.constituency, state="Selangor",
        )
        self.school_b = School.objects.create(
            moe_code="BBB0002", name="SJK(T) B", short_name="SJK(T) B",
            constituency=self.constituency, state="Selangor",
        )
        self.superadmin_user = User.objects.create_user("super", "super@tamilfoundation.org")
        self.superadmin = UserProfile.objects.create(
            user=self.superadmin_user, google_id="g-super",
            display_name="Super", role="SUPERADMIN",
        )
        self.moderator_user = User.objects.create_user("mod", "mod@tamilfoundation.org")
        self.moderator = UserProfile.objects.create(
            user=self.moderator_user, google_id="g-mod",
            display_name="Moderator", role="MODERATOR",
        )
        self.regular_user = User.objects.create_user("reg", "reg@gmail.com")
        self.regular = UserProfile.objects.create(
            user=self.regular_user, google_id="g-reg",
            display_name="Regular", role="USER",
        )
        self.school_admin_user = User.objects.create_user("sa", "aaa0001@moe.edu.my")
        self.school_admin = UserProfile.objects.create(
            user=self.school_admin_user, google_id="g-sa",
            display_name="Sch Admin", role="USER",
            admin_school=self.school_a,
        )

    def _auth(self, profile):
        session = self.client.session
        session["user_profile_id"] = profile.id
        session.save()


class AdminUserListTests(_BaseCase):
    url = "/api/v1/auth/admin/users/"

    def test_unauthenticated_denied(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_regular_user_denied(self):
        self._auth(self.regular)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_moderator_denied(self):
        self._auth(self.moderator)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_superadmin_allowed(self):
        self._auth(self.superadmin)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 4)

    def test_filter_by_role(self):
        self._auth(self.superadmin)
        resp = self.client.get(f"{self.url}?role=MODERATOR")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["results"][0]["display_name"], "Moderator")

    def test_filter_has_admin_school_true(self):
        self._auth(self.superadmin)
        resp = self.client.get(f"{self.url}?has_admin_school=true")
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["results"][0]["admin_school"]["moe_code"], "AAA0001")

    def test_filter_has_admin_school_false(self):
        self._auth(self.superadmin)
        resp = self.client.get(f"{self.url}?has_admin_school=false")
        self.assertEqual(resp.data["count"], 3)

    def test_filter_is_active(self):
        self._auth(self.superadmin)
        self.regular.is_active = False
        self.regular.save()
        resp = self.client.get(f"{self.url}?is_active=false")
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["results"][0]["display_name"], "Regular")

    def test_search_by_display_name(self):
        self._auth(self.superadmin)
        resp = self.client.get(f"{self.url}?search=Mod")
        self.assertEqual(resp.data["count"], 1)

    def test_search_by_email(self):
        self._auth(self.superadmin)
        resp = self.client.get(f"{self.url}?search=aaa0001")
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["results"][0]["display_name"], "Sch Admin")

    def test_search_by_school_code(self):
        self._auth(self.superadmin)
        resp = self.client.get(f"{self.url}?search=AAA0001")
        self.assertEqual(resp.data["count"], 1)

    def test_response_shape(self):
        self._auth(self.superadmin)
        resp = self.client.get(self.url)
        first = resp.data["results"][0]
        for key in ("id", "display_name", "avatar_url", "email", "role",
                    "admin_school", "points", "is_active",
                    "created_at", "updated_at"):
            self.assertIn(key, first)


class AdminUserUpdateTests(_BaseCase):
    def _url(self, profile_id):
        return f"/api/v1/auth/admin/users/{profile_id}/"

    def test_patch_role(self):
        self._auth(self.superadmin)
        resp = self.client.patch(self._url(self.regular.id), {"role": "MODERATOR"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.regular.refresh_from_db()
        self.assertEqual(self.regular.role, "MODERATOR")

    def test_patch_invalid_role(self):
        self._auth(self.superadmin)
        resp = self.client.patch(self._url(self.regular.id), {"role": "HACKER"}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_patch_assign_school(self):
        self._auth(self.superadmin)
        resp = self.client.patch(
            self._url(self.regular.id),
            {"admin_school": "BBB0002"}, format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.regular.refresh_from_db()
        self.assertEqual(self.regular.admin_school, self.school_b)

    def test_patch_unassign_school(self):
        self._auth(self.superadmin)
        resp = self.client.patch(
            self._url(self.school_admin.id),
            {"admin_school": None}, format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.school_admin.refresh_from_db()
        self.assertIsNone(self.school_admin.admin_school)

    def test_patch_school_not_found(self):
        self._auth(self.superadmin)
        resp = self.client.patch(
            self._url(self.regular.id),
            {"admin_school": "ZZZ9999"}, format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_patch_school_reassignment_strips_old_admin(self):
        """Assigning school_a to a second user should clear it from school_admin."""
        self._auth(self.superadmin)
        resp = self.client.patch(
            self._url(self.regular.id),
            {"admin_school": "AAA0001"}, format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.school_admin.refresh_from_db()
        self.assertIsNone(self.school_admin.admin_school)
        self.regular.refresh_from_db()
        self.assertEqual(self.regular.admin_school, self.school_a)

    def test_patch_deactivate(self):
        self._auth(self.superadmin)
        resp = self.client.patch(
            self._url(self.regular.id),
            {"is_active": False}, format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.regular.refresh_from_db()
        self.assertFalse(self.regular.is_active)

    def test_self_demote_role_forbidden(self):
        self._auth(self.superadmin)
        resp = self.client.patch(
            self._url(self.superadmin.id),
            {"role": "USER"}, format="json",
        )
        self.assertEqual(resp.status_code, 403)
        self.superadmin.refresh_from_db()
        self.assertEqual(self.superadmin.role, "SUPERADMIN")

    def test_self_deactivate_forbidden(self):
        self._auth(self.superadmin)
        resp = self.client.patch(
            self._url(self.superadmin.id),
            {"is_active": False}, format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_self_same_role_ok(self):
        """Superadmin setting their own role to SUPERADMIN (no-op) is allowed."""
        self._auth(self.superadmin)
        resp = self.client.patch(
            self._url(self.superadmin.id),
            {"role": "SUPERADMIN"}, format="json",
        )
        self.assertEqual(resp.status_code, 200)

    def test_non_superadmin_cannot_patch(self):
        self._auth(self.moderator)
        resp = self.client.patch(
            self._url(self.regular.id),
            {"role": "USER"}, format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_delete_soft_deactivates(self):
        self._auth(self.superadmin)
        resp = self.client.delete(self._url(self.regular.id))
        self.assertEqual(resp.status_code, 204)
        self.regular.refresh_from_db()
        self.assertFalse(self.regular.is_active)

    def test_delete_self_forbidden(self):
        self._auth(self.superadmin)
        resp = self.client.delete(self._url(self.superadmin.id))
        self.assertEqual(resp.status_code, 403)

    def test_delete_nonexistent_404(self):
        self._auth(self.superadmin)
        resp = self.client.delete(self._url(99999))
        self.assertEqual(resp.status_code, 404)


class MeUpdateTests(_BaseCase):
    url = "/api/v1/auth/me/"

    def test_patch_display_name(self):
        self._auth(self.regular)
        resp = self.client.patch(self.url, {"display_name": "New Name"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["display_name"], "New Name")
        self.regular.refresh_from_db()
        self.assertEqual(self.regular.display_name, "New Name")

    def test_patch_empty_display_name_rejected(self):
        self._auth(self.regular)
        resp = self.client.patch(self.url, {"display_name": "   "}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_patch_role_ignored(self):
        """Self-service PATCH cannot change role."""
        self._auth(self.regular)
        resp = self.client.patch(self.url, {"role": "SUPERADMIN"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.regular.refresh_from_db()
        self.assertEqual(self.regular.role, "USER")

    def test_patch_unauthenticated(self):
        resp = self.client.patch(self.url, {"display_name": "Hacker"}, format="json")
        self.assertEqual(resp.status_code, 401)


