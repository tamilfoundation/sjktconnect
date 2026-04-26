"""Sprint 14 — multipart photo upload + dedup + throttling."""

import io

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image
from rest_framework.test import APIClient

from accounts.models import UserProfile
from community.models import Suggestion
from community.tests.fixtures import valid_jpeg_bytes, valid_png_bytes
from outreach.services import image_processor as ip_module
from outreach.services.image_processor import (
    UploadValidationError,
    process_upload,
)
from schools.models import Constituency, School


class ImageProcessorUnitTest(TestCase):
    """Direct-call tests for the validation / resize / pHash service."""

    def test_happy_path_jpeg(self):
        result = process_upload(valid_jpeg_bytes(800, 600))
        self.assertEqual(result.content_type, "image/jpeg")
        self.assertEqual(result.extension, "jpg")
        self.assertEqual(result.width, 800)
        self.assertEqual(result.height, 600)
        self.assertTrue(result.phash)
        self.assertEqual(len(result.phash), 16)  # 64-bit phash → 16 hex chars

    def test_too_large_rejected(self):
        with self.assertRaises(UploadValidationError) as ctx:
            process_upload(b"x" * (ip_module.MAX_BYTES + 1))
        self.assertEqual(ctx.exception.code, "too_large")

    def test_too_small_rejected(self):
        with self.assertRaises(UploadValidationError) as ctx:
            process_upload(valid_jpeg_bytes(320, 200))
        self.assertEqual(ctx.exception.code, "too_small")

    def test_unsupported_format_rejected(self):
        # Pillow can write GIF; we feed it in to confirm the format gate works.
        img = Image.new("RGB", (800, 600), (10, 20, 30))
        buf = io.BytesIO()
        img.save(buf, format="GIF")
        with self.assertRaises(UploadValidationError) as ctx:
            process_upload(buf.getvalue())
        self.assertEqual(ctx.exception.code, "unsupported_format")

    def test_garbage_bytes_rejected(self):
        with self.assertRaises(UploadValidationError) as ctx:
            process_upload(b"not an image at all" * 100)
        self.assertEqual(ctx.exception.code, "invalid_image")

    def test_resize_caps_longest_edge_at_1600(self):
        result = process_upload(valid_jpeg_bytes(2400, 1800))
        self.assertEqual(result.width, 1600)
        self.assertEqual(result.height, 1200)

    def test_phash_stable_for_same_image(self):
        a = process_upload(valid_jpeg_bytes(800, 600, seed=42))
        b = process_upload(valid_jpeg_bytes(800, 600, seed=42))
        self.assertEqual(a.phash, b.phash)

    def test_phash_differs_for_different_images(self):
        a = process_upload(valid_jpeg_bytes(800, 600, seed=1))
        b = process_upload(valid_jpeg_bytes(800, 600, seed=999))
        self.assertNotEqual(a.phash, b.phash)


class PhotoUploadAPITest(TestCase):
    def setUp(self):
        cache.clear()  # throttle counters live in cache
        # DRF reads THROTTLE_RATES at class-definition time, so override_settings
        # doesn't propagate. Patch the throttle class rates directly so the
        # quota test can exhaust quickly without firing 5 real uploads.
        from community.api import throttles as t
        self._orig_user_rate = getattr(t.PhotoUploadUserThrottle, "rate", None)
        self._orig_school_rate = getattr(t.PhotoUploadSchoolThrottle, "rate", None)
        t.PhotoUploadUserThrottle.rate = "2/day"
        t.PhotoUploadSchoolThrottle.rate = "10/day"
        self.client = APIClient()
        self.constituency = Constituency.objects.create(
            code="P001", name="Test", state="Selangor",
        )
        self.school = School.objects.create(
            moe_code="ABC1234",
            name="SJK(T) Test",
            short_name="SJK(T) Test",
            constituency=self.constituency,
            state="Selangor",
        )
        self.user = User.objects.create_user("testuser")
        self.profile = UserProfile.objects.create(
            user=self.user,
            google_id="google-123",
            display_name="Test User",
        )
        session = self.client.session
        session["user_profile_id"] = self.profile.pk
        session.save()

    def tearDown(self):
        cache.clear()
        from community.api import throttles as t
        t.PhotoUploadUserThrottle.rate = self._orig_user_rate
        t.PhotoUploadSchoolThrottle.rate = self._orig_school_rate

    def _upload(self, raw=None, filename="test.jpg"):
        raw = raw if raw is not None else valid_jpeg_bytes()
        f = SimpleUploadedFile(filename, raw, content_type="image/jpeg")
        return self.client.post(
            f"/api/v1/schools/{self.school.moe_code}/suggestions/photo/",
            {"image": f, "note": "looks great"},
            format="multipart",
        )

    def test_happy_upload_creates_pending_suggestion(self):
        resp = self._upload()
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(Suggestion.objects.count(), 1)
        s = Suggestion.objects.get()
        self.assertEqual(s.type, "PHOTO_UPLOAD")
        self.assertEqual(s.status, "PENDING")
        self.assertEqual(s.user_id, self.profile.id)
        self.assertTrue(s.pending_image)
        self.assertEqual(len(s.phash), 16)

    def test_oversize_returns_413(self):
        resp = self._upload(raw=b"x" * (ip_module.MAX_BYTES + 1))
        self.assertEqual(resp.status_code, 413)
        self.assertEqual(resp.data["code"], "too_large")

    def test_undersize_returns_400(self):
        resp = self._upload(raw=valid_jpeg_bytes(320, 200))
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["code"], "too_small")

    def test_missing_image_field_returns_400(self):
        resp = self.client.post(
            f"/api/v1/schools/{self.school.moe_code}/suggestions/photo/",
            {"note": "hi"},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data["code"], "missing_image")

    def test_dedup_same_user_same_school_returns_409(self):
        first = self._upload()
        self.assertEqual(first.status_code, 201)
        second = self._upload()  # identical bytes → identical phash
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.data["code"], "duplicate")

    def test_user_throttle_429_after_quota(self):
        # Distinct seeds → distinct visual content → distinct pHashes.
        # Throttle is 2/user/day in this test's overridden settings.
        resp1 = self._upload(raw=valid_jpeg_bytes(seed=1))
        resp2 = self._upload(raw=valid_jpeg_bytes(seed=2))
        self.assertEqual(resp1.status_code, 201)
        self.assertEqual(resp2.status_code, 201)
        resp3 = self._upload(raw=valid_jpeg_bytes(seed=3))
        self.assertEqual(resp3.status_code, 429)

    def test_school_admin_cannot_upload_to_own_school(self):
        self.profile.admin_school = self.school
        self.profile.save()
        resp = self._upload()
        self.assertEqual(resp.status_code, 403)
        self.assertIn("admin image manager", resp.data["detail"].lower())

    def test_unauthenticated_rejected(self):
        self.client.logout()
        self.client.session.flush()
        new_client = APIClient()
        f = SimpleUploadedFile("test.jpg", valid_jpeg_bytes(), content_type="image/jpeg")
        resp = new_client.post(
            f"/api/v1/schools/{self.school.moe_code}/suggestions/photo/",
            {"image": f},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 403)
