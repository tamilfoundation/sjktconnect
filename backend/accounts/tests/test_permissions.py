from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User, AnonymousUser
from accounts.models import UserProfile
from accounts.permissions import (
    IsProfileAuthenticated,
    IsModeratorOrAbove,
    IsSuperAdmin,
    IsSchoolAdminForObject,
)
from schools.models import School


class PermissionTestBase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.school = School.objects.create(
            moe_code="TST0001", name="Test School",
            short_name="SJK(T) Test", state="Selangor", ppd="Test",
        )

    def _make_request(self, profile_id=None):
        request = self.factory.get("/fake/")
        request.session = {}
        if profile_id:
            request.session["user_profile_id"] = profile_id
        request.user = AnonymousUser()
        return request

    def _make_profile(self, role="USER", admin_school=None):
        user = User.objects.create_user(
            f"user_{UserProfile.objects.count()}", password="pass",
        )
        return UserProfile.objects.create(
            user=user,
            google_id=f"g-{user.username}",
            role=role,
            admin_school=admin_school,
        )


class IsProfileAuthenticatedTests(PermissionTestBase):
    def test_no_session_denied(self):
        request = self._make_request()
        self.assertFalse(IsProfileAuthenticated().has_permission(request, None))

    def test_valid_session_allowed(self):
        profile = self._make_profile()
        request = self._make_request(profile.id)
        self.assertTrue(IsProfileAuthenticated().has_permission(request, None))
        self.assertEqual(request.user_profile.id, profile.id)

    def test_inactive_profile_denied(self):
        profile = self._make_profile()
        profile.is_active = False
        profile.save()
        request = self._make_request(profile.id)
        self.assertFalse(IsProfileAuthenticated().has_permission(request, None))


class IsModeratorOrAboveTests(PermissionTestBase):
    def test_user_denied(self):
        profile = self._make_profile(role="USER")
        request = self._make_request(profile.id)
        IsProfileAuthenticated().has_permission(request, None)
        self.assertFalse(IsModeratorOrAbove().has_permission(request, None))

    def test_moderator_allowed(self):
        profile = self._make_profile(role="MODERATOR")
        request = self._make_request(profile.id)
        IsProfileAuthenticated().has_permission(request, None)
        self.assertTrue(IsModeratorOrAbove().has_permission(request, None))

    def test_superadmin_allowed(self):
        profile = self._make_profile(role="SUPERADMIN")
        request = self._make_request(profile.id)
        IsProfileAuthenticated().has_permission(request, None)
        self.assertTrue(IsModeratorOrAbove().has_permission(request, None))


class IsSuperAdminTests(PermissionTestBase):
    def test_moderator_denied(self):
        profile = self._make_profile(role="MODERATOR")
        request = self._make_request(profile.id)
        IsProfileAuthenticated().has_permission(request, None)
        self.assertFalse(IsSuperAdmin().has_permission(request, None))

    def test_superadmin_allowed(self):
        profile = self._make_profile(role="SUPERADMIN")
        request = self._make_request(profile.id)
        IsProfileAuthenticated().has_permission(request, None)
        self.assertTrue(IsSuperAdmin().has_permission(request, None))


class IsSchoolAdminForObjectTests(PermissionTestBase):
    def test_admin_for_own_school(self):
        profile = self._make_profile(admin_school=self.school)
        request = self._make_request(profile.id)
        IsProfileAuthenticated().has_permission(request, None)
        self.assertTrue(
            IsSchoolAdminForObject().has_object_permission(
                request, None, self.school,
            )
        )

    def test_admin_for_other_school_denied(self):
        other = School.objects.create(
            moe_code="TST0002", name="Other", short_name="SJK(T) Other",
            state="Perak", ppd="Test",
        )
        profile = self._make_profile(admin_school=other)
        request = self._make_request(profile.id)
        IsProfileAuthenticated().has_permission(request, None)
        self.assertFalse(
            IsSchoolAdminForObject().has_object_permission(
                request, None, self.school,
            )
        )
