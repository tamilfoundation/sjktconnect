"""Tests for school history field + serializer behaviour (Sprint 31, 2026-06-27).

Covers:
- Model JSONField default
- SchoolDetailSerializer exposes per-locale history + sources + status
- SchoolEditSerializer accepts valid per-locale dict + URL list
- Validation: rejects unknown locales, non-string values, oversize text,
  non-list sources, malformed URLs
- update() auto-flips status to SCHOOL_REVIEWED when a non-SUPERADMIN edits
- update() preserves explicit status when SUPERADMIN edits
- update() bumps history_updated_at on content change
"""

from unittest.mock import MagicMock

import pytest

from schools.api.serializers import (
    SchoolDetailSerializer,
    SchoolEditSerializer,
)
from schools.models import School


@pytest.fixture
def school(db):
    return School.objects.create(
        moe_code="TEST0001",
        name="SJK(T) Test School",
        short_name="SJK(T) Test",
        state="Selangor",
        is_active=True,
    )


@pytest.mark.django_db
class TestSchoolHistoryModel:
    def test_history_defaults_to_empty_dict(self, school):
        assert school.history == {}

    def test_history_source_urls_defaults_to_empty_list(self, school):
        assert school.history_source_urls == []

    def test_history_status_defaults_to_unverified(self, school):
        assert school.history_status == "UNVERIFIED"

    def test_history_updated_at_defaults_to_none(self, school):
        assert school.history_updated_at is None


@pytest.mark.django_db
class TestSchoolDetailSerializerHistory:
    def test_history_fields_exposed_when_empty(self, school):
        data = SchoolDetailSerializer(school).data
        assert data["history"] == {}
        assert data["history_source_urls"] == []
        assert data["history_status"] == "UNVERIFIED"
        assert data["history_updated_at"] is None

    def test_history_fields_exposed_when_populated(self, school):
        school.history = {"en": "Founded 1946.", "ms": "Ditubuhkan pada 1946."}
        school.history_source_urls = ["https://example.com/source"]
        school.history_status = "SCHOOL_REVIEWED"
        school.save()
        data = SchoolDetailSerializer(school).data
        assert data["history"]["en"] == "Founded 1946."
        assert data["history"]["ms"] == "Ditubuhkan pada 1946."
        assert data["history_source_urls"] == ["https://example.com/source"]
        assert data["history_status"] == "SCHOOL_REVIEWED"


@pytest.mark.django_db
class TestSchoolEditSerializerHistoryValidation:
    def _make_request(self, profile=None):
        req = MagicMock()
        req.session = {}
        if profile:
            req.session["user_profile_id"] = profile.id
        return req

    def test_accepts_valid_per_locale_dict(self, school):
        s = SchoolEditSerializer(school, data={"history": {"en": "x"}}, partial=True)
        assert s.is_valid(), s.errors

    def test_accepts_all_three_locales(self, school):
        s = SchoolEditSerializer(school, data={
            "history": {"en": "x", "ms": "y", "ta": "z"}
        }, partial=True)
        assert s.is_valid(), s.errors

    def test_rejects_unknown_locale(self, school):
        s = SchoolEditSerializer(school, data={
            "history": {"en": "x", "fr": "frog"}
        }, partial=True)
        assert not s.is_valid()
        assert "fr" in str(s.errors["history"])

    def test_rejects_non_string_value(self, school):
        s = SchoolEditSerializer(school, data={"history": {"en": 123}}, partial=True)
        assert not s.is_valid()

    def test_rejects_oversize_text(self, school):
        s = SchoolEditSerializer(school, data={
            "history": {"en": "x" * 5001}
        }, partial=True)
        assert not s.is_valid()
        assert "too long" in str(s.errors["history"])

    def test_rejects_non_list_sources(self, school):
        s = SchoolEditSerializer(school, data={
            "history_source_urls": "not-a-list"
        }, partial=True)
        assert not s.is_valid()

    def test_rejects_too_many_sources(self, school):
        s = SchoolEditSerializer(school, data={
            "history_source_urls": [f"https://e.com/{i}" for i in range(11)]
        }, partial=True)
        assert not s.is_valid()

    def test_rejects_malformed_source_url(self, school):
        s = SchoolEditSerializer(school, data={
            "history_source_urls": ["javascript:alert(1)"]
        }, partial=True)
        assert not s.is_valid()


@pytest.mark.django_db
class TestSchoolEditSerializerHistoryUpdate:
    def _superadmin_request(self, db):
        from accounts.models import UserProfile
        from django.contrib.auth.models import User
        u = User.objects.create_user(username="admin", password="x")
        profile = UserProfile.objects.create(user=u, role="SUPERADMIN")
        req = MagicMock()
        req.session = {"user_profile_id": profile.id}
        return req

    def _regular_request(self, db):
        from accounts.models import UserProfile
        from django.contrib.auth.models import User
        u = User.objects.create_user(username="user", password="x")
        profile = UserProfile.objects.create(user=u, role="USER")
        req = MagicMock()
        req.session = {"user_profile_id": profile.id}
        return req

    def test_non_superadmin_edit_flips_status_to_school_reviewed(self, db, school):
        req = self._regular_request(db)
        s = SchoolEditSerializer(school, data={
            "history": {"en": "Edited by school admin."},
            "history_status": "VERIFIED",  # client attempt to forge
        }, partial=True, context={"request": req})
        s.is_valid(raise_exception=True)
        updated = s.save()
        assert updated.history_status == "SCHOOL_REVIEWED"  # ignored client value

    def test_superadmin_can_set_verified_status(self, db, school):
        req = self._superadmin_request(db)
        s = SchoolEditSerializer(school, data={
            "history": {"en": "Verified by superadmin."},
            "history_status": "VERIFIED",
        }, partial=True, context={"request": req})
        s.is_valid(raise_exception=True)
        updated = s.save()
        assert updated.history_status == "VERIFIED"

    def test_history_updated_at_bumps_on_content_change(self, db, school):
        req = self._superadmin_request(db)
        assert school.history_updated_at is None
        s = SchoolEditSerializer(school, data={
            "history": {"en": "Initial content."},
        }, partial=True, context={"request": req})
        s.is_valid(raise_exception=True)
        updated = s.save()
        assert updated.history_updated_at is not None

    def test_history_updated_at_not_bumped_when_history_unchanged(self, db, school):
        req = self._superadmin_request(db)
        s = SchoolEditSerializer(school, data={
            "name_tamil": "ஒரு பெயர்",  # change unrelated field
        }, partial=True, context={"request": req})
        s.is_valid(raise_exception=True)
        updated = s.save()
        assert updated.history_updated_at is None  # untouched
