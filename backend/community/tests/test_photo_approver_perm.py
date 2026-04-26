"""Sprint 14 — IsPhotoApprover permission matrix.

Photos may be approved/rejected by SUPERADMIN OR the bound school admin
ONLY. MODERATOR is intentionally NOT a photo approver, and a school admin
of a DIFFERENT school cannot approve.
"""

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from community.models import Suggestion
from community.tests.fixtures import valid_png_bytes
from schools.models import Constituency, School


class PhotoApproverPermTest(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.constituency = Constituency.objects.create(
            code="P001", name="Test", state="Selangor",
        )
        self.school = School.objects.create(
            moe_code="ABC1234",
            name="SJK(T) Test", short_name="SJK(T) Test",
            constituency=self.constituency, state="Selangor",
        )
        self.other_school = School.objects.create(
            moe_code="XYZ9999",
            name="SJK(T) Other", short_name="SJK(T) Other",
            constituency=self.constituency, state="Selangor",
        )

        self.uploader = UserProfile.objects.create(
            user=User.objects.create_user("up"),
            google_id="g-up", display_name="Up",
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
        self.bound_admin = UserProfile.objects.create(
            user=User.objects.create_user("bound"),
            google_id="g-bound", display_name="Bound",
            admin_school=self.school,
        )
        self.other_admin = UserProfile.objects.create(
            user=User.objects.create_user("other"),
            google_id="g-other", display_name="Other",
            admin_school=self.other_school,
        )

    def _auth(self, profile):
        session = self.client.session
        session["user_profile_id"] = profile.pk
        session.save()

    def _make_pending(self):
        s = Suggestion.objects.create(
            school=self.school, user=self.uploader, type="PHOTO_UPLOAD",
        )
        s.pending_image.save("p.png", ContentFile(valid_png_bytes()), save=True)
        return s

    def test_superadmin_can_approve(self):
        self._auth(self.superadmin)
        s = self._make_pending()
        resp = self.client.post(f"/api/v1/suggestions/{s.pk}/approve/")
        self.assertEqual(resp.status_code, 200, resp.data)

    def test_bound_school_admin_can_approve(self):
        self._auth(self.bound_admin)
        s = self._make_pending()
        resp = self.client.post(f"/api/v1/suggestions/{s.pk}/approve/")
        self.assertEqual(resp.status_code, 200, resp.data)

    def test_moderator_cannot_approve_photo(self):
        """KEY: MODERATOR is excluded from photo approval (Sprint 14 design)."""
        self._auth(self.moderator)
        s = self._make_pending()
        resp = self.client.post(f"/api/v1/suggestions/{s.pk}/approve/")
        self.assertEqual(resp.status_code, 403)

    def test_other_school_admin_cannot_approve(self):
        self._auth(self.other_admin)
        s = self._make_pending()
        resp = self.client.post(f"/api/v1/suggestions/{s.pk}/approve/")
        self.assertEqual(resp.status_code, 403)

    def test_regular_user_cannot_approve(self):
        self._auth(self.regular)
        s = self._make_pending()
        resp = self.client.post(f"/api/v1/suggestions/{s.pk}/approve/")
        self.assertEqual(resp.status_code, 403)

    def test_moderator_cannot_reject_photo(self):
        self._auth(self.moderator)
        s = self._make_pending()
        resp = self.client.post(
            f"/api/v1/suggestions/{s.pk}/reject/",
            {"reason": "no"}, format="json",
        )
        self.assertEqual(resp.status_code, 403)
