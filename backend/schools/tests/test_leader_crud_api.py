"""Sprint 20 — SchoolLeader CRUD endpoints.

Permission matrix mirrors community/IsPhotoApprover: SUPERADMIN OR
the bound admin of THIS school. MODERATOR is NOT special-cased here —
leadership is a school-internal concern.
"""

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from schools.models import Constituency, School, SchoolLeader


def _make_profile(*, role="USER", admin_school=None, email_suffix="x"):
    user = User.objects.create_user(f"u{email_suffix}", f"u{email_suffix}@example.com")
    return UserProfile.objects.create(
        user=user,
        google_id=f"g-{email_suffix}",
        display_name=f"User {email_suffix}",
        role=role,
        admin_school=admin_school,
    )


def _signin(client, profile):
    session = client.session
    session["user_profile_id"] = profile.id
    session.save()


class SchoolLeaderCRUDPermissionTests(TestCase):
    """Sprint 20: 5-role permission matrix for create/update/delete."""

    def setUp(self):
        self.client = APIClient()
        self.constituency = Constituency.objects.create(
            code="P140", name="Segamat", state="Johor"
        )
        self.school = School.objects.create(
            moe_code="JBD0050",
            name="SJK(T) Ladang Bikam",
            short_name="SJK(T) Ladang Bikam",
            state="Johor",
            constituency=self.constituency,
        )
        self.other_school = School.objects.create(
            moe_code="JBD0099",
            name="SJK(T) Other",
            short_name="SJK(T) Other",
            state="Johor",
            constituency=self.constituency,
        )
        self.create_url = f"/api/v1/schools/{self.school.moe_code}/leaders/"

    def _post(self, profile, body=None):
        client = APIClient()
        if profile is not None:
            _signin(client, profile)
        return client.post(
            self.create_url,
            body or {"role": "headmaster", "name": "Pn. Test HM"},
            format="json",
        )

    def test_anonymous_denied(self):
        self.assertEqual(self.client.post(self.create_url, {}, format="json").status_code, 403)

    def test_regular_user_denied(self):
        profile = _make_profile(role="USER", email_suffix="reg")
        self.assertEqual(self._post(profile).status_code, 403)

    def test_moderator_denied(self):
        # Sprint 20 matches IsPhotoApprover: MODERATOR has no special role here.
        profile = _make_profile(role="MODERATOR", email_suffix="mod")
        self.assertEqual(self._post(profile).status_code, 403)

    def test_admin_of_DIFFERENT_school_denied(self):
        profile = _make_profile(role="USER", admin_school=self.other_school, email_suffix="other")
        self.assertEqual(self._post(profile).status_code, 403)

    def test_admin_of_THIS_school_allowed(self):
        profile = _make_profile(role="USER", admin_school=self.school, email_suffix="own")
        response = self._post(profile)
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.data["name"], "Pn. Test HM")
        self.assertEqual(response.data["role"], "headmaster")
        self.assertEqual(response.data["role_display"], "Headmaster")

    def test_superadmin_allowed_for_any_school(self):
        profile = _make_profile(role="SUPERADMIN", email_suffix="sa")
        response = self._post(profile)
        self.assertEqual(response.status_code, 201)


class SchoolLeaderCRUDBehaviourTests(TestCase):
    """Happy path + edge cases on create/update/delete."""

    def setUp(self):
        self.client = APIClient()
        self.constituency = Constituency.objects.create(
            code="P140", name="Segamat", state="Johor"
        )
        self.school = School.objects.create(
            moe_code="JBD0050",
            name="SJK(T) Ladang Bikam",
            short_name="SJK(T) Ladang Bikam",
            state="Johor",
            constituency=self.constituency,
        )
        self.profile = _make_profile(role="USER", admin_school=self.school, email_suffix="hm")
        _signin(self.client, self.profile)
        self.create_url = f"/api/v1/schools/{self.school.moe_code}/leaders/"

    def test_create_includes_phone_and_email(self):
        response = self.client.post(
            self.create_url,
            {
                "role": "headmaster",
                "name": "Pn. Devi",
                "phone": "07-1234567",
                "email": "hm@example.com",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        leader = SchoolLeader.objects.get(pk=response.data["id"])
        # Sprint 28: phone is auto-normalised to +60-X XXX XXXX on save.
        self.assertEqual(leader.phone, "+60-7 123 4567")
        self.assertEqual(leader.email, "hm@example.com")

    def test_duplicate_role_returns_409_slot_taken(self):
        SchoolLeader.objects.create(
            school=self.school, role="headmaster", name="Existing HM"
        )
        response = self.client.post(
            self.create_url,
            {"role": "headmaster", "name": "Replacement"},
            format="json",
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "role_taken")

    def test_invalid_role_returns_400(self):
        response = self.client.post(
            self.create_url,
            {"role": "supreme_overlord", "name": "X"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_missing_name_returns_400(self):
        response = self.client.post(
            self.create_url,
            {"role": "headmaster"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_create_for_unknown_school_returns_404(self):
        response = self.client.post(
            "/api/v1/schools/UNKNOWN/leaders/",
            {"role": "headmaster", "name": "X"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_patch_updates_name_phone_email(self):
        leader = SchoolLeader.objects.create(
            school=self.school, role="headmaster", name="Old Name"
        )
        response = self.client.patch(
            f"{self.create_url}{leader.pk}/",
            {"name": "New Name", "phone": "07-9999999"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        leader.refresh_from_db()
        self.assertEqual(leader.name, "New Name")
        # Sprint 28: phone is auto-normalised on save.
        self.assertEqual(leader.phone, "+60-7 999 9999")

    def test_patch_does_not_change_role(self):
        leader = SchoolLeader.objects.create(
            school=self.school, role="headmaster", name="HM"
        )
        response = self.client.patch(
            f"{self.create_url}{leader.pk}/",
            {"role": "board_chair", "name": "Should Stay HM"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        leader.refresh_from_db()
        self.assertEqual(leader.role, "headmaster")  # unchanged
        self.assertEqual(leader.name, "Should Stay HM")

    def test_delete_soft_deletes(self):
        leader = SchoolLeader.objects.create(
            school=self.school, role="headmaster", name="HM"
        )
        response = self.client.delete(f"{self.create_url}{leader.pk}/")
        self.assertEqual(response.status_code, 204)
        leader.refresh_from_db()
        self.assertFalse(leader.is_active)

    def test_delete_then_recreate_same_role_allowed(self):
        # The unique constraint is on (school, role) WHERE is_active=True,
        # so soft-deleting frees the slot.
        leader = SchoolLeader.objects.create(
            school=self.school, role="headmaster", name="Old HM"
        )
        self.client.delete(f"{self.create_url}{leader.pk}/")
        response = self.client.post(
            self.create_url,
            {"role": "headmaster", "name": "New HM"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)

    def test_patch_or_delete_unknown_leader_returns_404(self):
        response = self.client.patch(
            f"{self.create_url}99999/",
            {"name": "x"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_patch_leader_belonging_to_another_school_returns_404(self):
        # Even SUPERADMIN can't reach a leader via the wrong school's URL.
        other = School.objects.create(
            moe_code="JBD0099", name="Other", short_name="Other",
            state="Johor", constituency=self.constituency,
        )
        leader = SchoolLeader.objects.create(
            school=other, role="headmaster", name="Other HM"
        )
        response = self.client.patch(
            f"{self.create_url}{leader.pk}/",
            {"name": "x"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_create_rejects_multi_number_phone(self):
        """Sprint 26 #1: leader phone validated same as School.phone."""
        response = self.client.post(
            self.create_url,
            {
                "role": "headmaster",
                "name": "Pn. Devi",
                "phone": "07-1234567/011-9876543",
                "email": "hm@example.com",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("phone", response.data)

    def test_patch_rejects_multi_number_phone(self):
        leader = SchoolLeader.objects.create(
            school=self.school, role="headmaster",
            name="Pn. Devi", phone="07-1234567",
        )
        response = self.client.patch(
            f"{self.create_url}{leader.pk}/",
            {"phone": "07-1234567/011-9876543"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
