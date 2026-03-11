# Suggestion Workflow (Sprint 8.2) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Community users can suggest school data corrections, upload photos, and leave notes. Moderators and school admins review and approve. Points awarded on approval.

**Architecture:** New `community` Django app with Suggestion model. SchoolImage gets `position` and `uploaded_by` fields. Approval auto-applies changes to School model. Frontend: suggest form on school pages, moderation queue on dashboard, image manager for school admins.

**Tech Stack:** Django REST Framework, Next.js 14 App Router, NextAuth.js v5, next-intl, Tailwind CSS.

---

### Task 1: Community App + Suggestion Model

**Files:**
- Create: `backend/community/__init__.py`
- Create: `backend/community/models.py`
- Create: `backend/community/admin.py`
- Create: `backend/community/apps.py`
- Modify: `backend/sjktconnect/settings/base.py` — add `"community"` to INSTALLED_APPS
- Test: `backend/community/tests/__init__.py`
- Test: `backend/community/tests/test_models.py`

**Step 1: Create the app skeleton**

```bash
cd backend && python manage.py startapp community
```

Delete the auto-generated `views.py`, `tests.py` (we'll use a tests/ package), and `migrations/` (we'll makemigrations after).

**Step 2: Write the Suggestion model**

`backend/community/models.py`:
```python
from django.db import models


class Suggestion(models.Model):
    class Type(models.TextChoices):
        DATA_CORRECTION = "DATA_CORRECTION", "Data Correction"
        PHOTO_UPLOAD = "PHOTO_UPLOAD", "Photo Upload"
        NOTE = "NOTE", "Note"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    POINTS_MAP = {
        "DATA_CORRECTION": 2,
        "PHOTO_UPLOAD": 3,
        "NOTE": 1,
    }

    SUGGESTIBLE_FIELDS = [
        "phone", "fax", "address", "postcode", "city",
        "gps_lat", "gps_lng", "grade", "assistance_type",
        "bank_name", "bank_account_number", "bank_account_name",
    ]

    school = models.ForeignKey(
        "schools.School", on_delete=models.CASCADE, related_name="suggestions"
    )
    user = models.ForeignKey(
        "accounts.UserProfile", on_delete=models.CASCADE, related_name="suggestions"
    )
    type = models.CharField(max_length=20, choices=Type.choices)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    field_name = models.CharField(max_length=50, blank=True, default="")
    current_value = models.TextField(blank=True, default="")
    suggested_value = models.TextField(blank=True, default="")
    note = models.TextField(blank=True, default="")
    image = models.BinaryField(blank=True, default=b"")
    reviewed_by = models.ForeignKey(
        "accounts.UserProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_suggestions",
    )
    review_note = models.TextField(blank=True, default="")
    points_awarded = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.school_id} — {self.get_type_display()} ({self.get_status_display()})"
```

**Step 3: Write admin**

`backend/community/admin.py`:
```python
from django.contrib import admin
from community.models import Suggestion


@admin.register(Suggestion)
class SuggestionAdmin(admin.ModelAdmin):
    list_display = ["school", "user", "type", "status", "field_name", "created_at"]
    list_filter = ["type", "status"]
    readonly_fields = ["created_at", "updated_at"]
```

**Step 4: Add to INSTALLED_APPS**

In `backend/sjktconnect/settings/base.py`, add `"community"` after `"accounts"` in INSTALLED_APPS.

**Step 5: Write model tests**

`backend/community/tests/test_models.py`:
```python
from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from community.models import Suggestion
from schools.models import Constituency, School


class SuggestionModelTest(TestCase):
    def setUp(self):
        self.constituency = Constituency.objects.create(
            code="P001", name="Test", state="Selangor"
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

    def test_create_data_correction(self):
        s = Suggestion.objects.create(
            school=self.school,
            user=self.profile,
            type=Suggestion.Type.DATA_CORRECTION,
            field_name="phone",
            current_value="03-1234567",
            suggested_value="03-7654321",
        )
        self.assertEqual(s.status, Suggestion.Status.PENDING)
        self.assertEqual(str(s), "ABC1234 — Data Correction (Pending)")

    def test_create_photo_upload(self):
        s = Suggestion.objects.create(
            school=self.school,
            user=self.profile,
            type=Suggestion.Type.PHOTO_UPLOAD,
            image=b"fake-png-bytes",
        )
        self.assertEqual(s.type, Suggestion.Type.PHOTO_UPLOAD)

    def test_create_note(self):
        s = Suggestion.objects.create(
            school=self.school,
            user=self.profile,
            type=Suggestion.Type.NOTE,
            note="This school has moved to a new building",
        )
        self.assertEqual(s.type, Suggestion.Type.NOTE)

    def test_points_map(self):
        self.assertEqual(Suggestion.POINTS_MAP["DATA_CORRECTION"], 2)
        self.assertEqual(Suggestion.POINTS_MAP["PHOTO_UPLOAD"], 3)
        self.assertEqual(Suggestion.POINTS_MAP["NOTE"], 1)

    def test_suggestible_fields_list(self):
        self.assertIn("phone", Suggestion.SUGGESTIBLE_FIELDS)
        self.assertNotIn("enrolment", Suggestion.SUGGESTIBLE_FIELDS)
        self.assertNotIn("email", Suggestion.SUGGESTIBLE_FIELDS)
```

**Step 6: Make migration and run tests**

```bash
cd backend && python manage.py makemigrations community -n suggestion_model
python -m pytest community/ -v
```

Expected: 5 tests PASS.

**Step 7: Commit**

```bash
git add backend/community/ backend/sjktconnect/settings/base.py
git commit -m "feat: community app with Suggestion model"
```

---

### Task 2: SchoolImage — Add position and uploaded_by

**Files:**
- Modify: `backend/outreach/models.py:6-36`
- Create: `backend/outreach/migrations/0003_add_position_uploaded_by.py`
- Test: `backend/outreach/tests/test_models.py` (add tests)

**Step 1: Write failing test**

Add to `backend/outreach/tests/test_models.py`:
```python
def test_school_image_has_position_field(self):
    img = SchoolImage.objects.create(
        school=self.school, image_url="https://example.com/img.jpg",
        source="MANUAL", position=3,
    )
    self.assertEqual(img.position, 3)

def test_school_image_ordering_by_position(self):
    SchoolImage.objects.create(
        school=self.school, image_url="https://example.com/b.jpg",
        source="MANUAL", position=2,
    )
    SchoolImage.objects.create(
        school=self.school, image_url="https://example.com/a.jpg",
        source="MANUAL", position=1,
    )
    images = list(SchoolImage.objects.filter(school=self.school))
    self.assertEqual(images[0].position, 1)
    self.assertEqual(images[1].position, 2)
```

**Step 2: Add fields to SchoolImage**

In `backend/outreach/models.py`, add after `attribution`:
```python
position = models.PositiveIntegerField(
    default=0, help_text="Display order (0 = auto, lower = first)"
)
uploaded_by = models.ForeignKey(
    "accounts.UserProfile",
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="uploaded_images",
)
```

Update Meta ordering to `["position", "-is_primary", "-created_at"]`.

Add `COMMUNITY` to source TextChoices:
```python
COMMUNITY = "COMMUNITY", "Community Upload"
```

**Step 3: Make migration and run tests**

```bash
cd backend && python manage.py makemigrations outreach -n add_position_uploaded_by
python -m pytest outreach/ -v
```

**Step 4: Commit**

```bash
git add backend/outreach/
git commit -m "feat: add position and uploaded_by to SchoolImage"
```

---

### Task 3: Suggestion API — Create and List

**Files:**
- Create: `backend/community/api/__init__.py`
- Create: `backend/community/api/serializers.py`
- Create: `backend/community/api/views.py`
- Create: `backend/community/api/urls.py`
- Modify: `backend/sjktconnect/urls.py` — add community API urls
- Test: `backend/community/tests/test_api.py`

**Step 1: Write serializers**

`backend/community/api/serializers.py`:
```python
from rest_framework import serializers

from community.models import Suggestion


class SuggestionCreateSerializer(serializers.ModelSerializer):
    image = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Suggestion
        fields = [
            "type", "field_name", "suggested_value", "note", "image",
        ]

    def validate_field_name(self, value):
        if value and value not in Suggestion.SUGGESTIBLE_FIELDS:
            # Allow "leadership" as a special case
            if not value.startswith("leadership_"):
                raise serializers.ValidationError(
                    f"Field '{value}' is not suggestible."
                )
        return value

    def validate(self, data):
        if data["type"] == "DATA_CORRECTION" and not data.get("field_name"):
            raise serializers.ValidationError(
                "field_name is required for data corrections."
            )
        if data["type"] == "PHOTO_UPLOAD" and not data.get("image"):
            raise serializers.ValidationError(
                "image is required for photo uploads."
            )
        return data


class SuggestionListSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.display_name", read_only=True)
    school_name = serializers.CharField(source="school.short_name", read_only=True)
    reviewed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Suggestion
        fields = [
            "id", "school", "user_name", "school_name", "type", "status",
            "field_name", "current_value", "suggested_value", "note",
            "reviewed_by_name", "review_note", "points_awarded",
            "created_at",
        ]

    def get_reviewed_by_name(self, obj):
        if obj.reviewed_by:
            return obj.reviewed_by.display_name
        return None
```

**Step 2: Write views**

`backend/community/api/views.py`:
```python
import base64

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from accounts.permissions import IsProfileAuthenticated
from community.api.serializers import (
    SuggestionCreateSerializer,
    SuggestionListSerializer,
)
from community.models import Suggestion
from schools.models import School


@api_view(["GET", "POST"])
@permission_classes([IsProfileAuthenticated])
def school_suggestions_view(request, moe_code):
    school = get_object_or_404(School, moe_code=moe_code)
    profile = request.user_profile

    if request.method == "GET":
        suggestions = Suggestion.objects.filter(school=school)
        serializer = SuggestionListSerializer(suggestions, many=True)
        return Response(serializer.data)

    # POST — create suggestion
    if profile.admin_school_id == school.moe_code:
        return Response(
            {"detail": "Cannot suggest changes to your own school. Edit directly."},
            status=status.HTTP_403_FORBIDDEN,
        )

    serializer = SuggestionCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    # Snapshot current value for data corrections
    current_value = ""
    if data.get("field_name") and hasattr(school, data["field_name"]):
        current_value = str(getattr(school, data["field_name"]) or "")

    # Handle base64 image
    image_bytes = b""
    if data.get("image"):
        try:
            image_bytes = base64.b64decode(data["image"])
        except Exception:
            return Response(
                {"detail": "Invalid image data."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    suggestion = Suggestion.objects.create(
        school=school,
        user=profile,
        type=data["type"],
        field_name=data.get("field_name", ""),
        current_value=current_value,
        suggested_value=data.get("suggested_value", ""),
        note=data.get("note", ""),
        image=image_bytes,
    )

    return Response(
        SuggestionListSerializer(suggestion).data,
        status=status.HTTP_201_CREATED,
    )
```

**Step 3: Write URLs**

`backend/community/api/urls.py`:
```python
from django.urls import path

from community.api.views import school_suggestions_view

urlpatterns = [
    path(
        "schools/<str:moe_code>/suggestions/",
        school_suggestions_view,
        name="school-suggestions",
    ),
]
```

Add to `backend/sjktconnect/urls.py`:
```python
path("api/v1/", include("community.api.urls")),
```

**Step 4: Write API tests**

`backend/community/tests/test_api.py`:
```python
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from community.models import Suggestion
from schools.models import Constituency, School


class SuggestionAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.constituency = Constituency.objects.create(
            code="P001", name="Test", state="Selangor"
        )
        self.school = School.objects.create(
            moe_code="ABC1234",
            name="SJK(T) Test",
            short_name="SJK(T) Test",
            constituency=self.constituency,
            state="Selangor",
            phone="03-1234567",
        )
        self.user = User.objects.create_user("testuser")
        self.profile = UserProfile.objects.create(
            user=self.user,
            google_id="google-123",
            display_name="Test User",
        )

    def _auth(self, profile=None):
        p = profile or self.profile
        session = self.client.session
        session["user_profile_id"] = p.pk
        session.save()

    def test_create_data_correction(self):
        self._auth()
        resp = self.client.post(
            "/api/v1/schools/ABC1234/suggestions/",
            {
                "type": "DATA_CORRECTION",
                "field_name": "phone",
                "suggested_value": "03-9999999",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["current_value"], "03-1234567")
        self.assertEqual(resp.data["suggested_value"], "03-9999999")

    def test_create_note(self):
        self._auth()
        resp = self.client.post(
            "/api/v1/schools/ABC1234/suggestions/",
            {
                "type": "NOTE",
                "note": "School has relocated to a new building",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)

    def test_blocked_for_own_school(self):
        self.profile.admin_school = self.school
        self.profile.save()
        self._auth()
        resp = self.client.post(
            "/api/v1/schools/ABC1234/suggestions/",
            {"type": "NOTE", "note": "test"},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_rejects_non_suggestible_field(self):
        self._auth()
        resp = self.client.post(
            "/api/v1/schools/ABC1234/suggestions/",
            {
                "type": "DATA_CORRECTION",
                "field_name": "enrolment",
                "suggested_value": "500",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_list_suggestions(self):
        self._auth()
        Suggestion.objects.create(
            school=self.school, user=self.profile,
            type="NOTE", note="Test note",
        )
        resp = self.client.get("/api/v1/schools/ABC1234/suggestions/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)

    def test_unauthenticated_rejected(self):
        resp = self.client.post(
            "/api/v1/schools/ABC1234/suggestions/",
            {"type": "NOTE", "note": "test"},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)
```

**Step 5: Run tests**

```bash
python -m pytest community/ -v
```

Expected: 11 tests PASS (5 model + 6 API).

**Step 6: Commit**

```bash
git add backend/community/api/ backend/sjktconnect/urls.py
git commit -m "feat: suggestion create and list API endpoints"
```

---

### Task 4: Moderation Queue + Approve/Reject

**Files:**
- Modify: `backend/community/api/views.py`
- Modify: `backend/community/api/urls.py`
- Create: `backend/community/services.py`
- Test: `backend/community/tests/test_approval.py`

**Step 1: Write the approval service**

`backend/community/services.py`:
```python
from django.db import transaction

from community.models import Suggestion
from outreach.models import SchoolImage


def approve_suggestion(suggestion, reviewer):
    """Approve a suggestion: apply changes, award points."""
    with transaction.atomic():
        suggestion.status = Suggestion.Status.APPROVED
        suggestion.reviewed_by = reviewer

        # Award points (not for own school)
        if suggestion.user.admin_school_id != suggestion.school_id:
            points = Suggestion.POINTS_MAP.get(suggestion.type, 0)
            suggestion.points_awarded = points
            suggestion.user.points += points
            suggestion.user.save(update_fields=["points"])

        # Apply the change
        if suggestion.type == Suggestion.Type.DATA_CORRECTION:
            _apply_data_correction(suggestion)
        elif suggestion.type == Suggestion.Type.PHOTO_UPLOAD:
            _apply_photo_upload(suggestion)
        # NOTE type: no auto-apply, moderator acts manually

        suggestion.save()

    return suggestion


def reject_suggestion(suggestion, reviewer, reason=""):
    suggestion.status = Suggestion.Status.REJECTED
    suggestion.reviewed_by = reviewer
    suggestion.review_note = reason
    suggestion.save()
    return suggestion


def _apply_data_correction(suggestion):
    """Update the school field with the suggested value."""
    school = suggestion.school
    field = suggestion.field_name

    if field.startswith("leadership_"):
        # Handle leadership changes separately
        return

    if field in Suggestion.SUGGESTIBLE_FIELDS and hasattr(school, field):
        setattr(school, field, suggestion.suggested_value)
        school.save(update_fields=[field, "updated_at"])


def _apply_photo_upload(suggestion):
    """Create a SchoolImage from the suggestion's image bytes."""
    if not suggestion.image:
        return

    # Count existing images
    existing_count = SchoolImage.objects.filter(school=suggestion.school).count()
    if existing_count >= 10:
        return  # Max 10 images per school

    max_position = (
        SchoolImage.objects.filter(school=suggestion.school)
        .order_by("-position")
        .values_list("position", flat=True)
        .first()
    ) or 0

    # Store as a served URL via the suggestion image endpoint
    SchoolImage.objects.create(
        school=suggestion.school,
        image_url=f"/api/v1/suggestions/{suggestion.pk}/image/",
        source="COMMUNITY",
        position=max_position + 1,
        uploaded_by=suggestion.user,
    )
```

**Step 2: Write moderation views**

Add to `backend/community/api/views.py`:
```python
from accounts.permissions import IsModeratorOrAbove, IsSchoolAdminForObject
from community.services import approve_suggestion, reject_suggestion


@api_view(["GET"])
@permission_classes([IsProfileAuthenticated, IsModeratorOrAbove])
def pending_suggestions_view(request):
    """Moderation queue — all pending suggestions."""
    qs = Suggestion.objects.filter(status=Suggestion.Status.PENDING)

    # School admins see only their school
    profile = request.user_profile
    if profile.role == "USER" and profile.admin_school_id:
        qs = qs.filter(school_id=profile.admin_school_id)

    serializer = SuggestionListSerializer(qs, many=True)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsProfileAuthenticated])
def approve_suggestion_view(request, pk):
    suggestion = get_object_or_404(Suggestion, pk=pk, status=Suggestion.Status.PENDING)
    profile = request.user_profile

    # Check permission: moderator+ or school admin for this school
    if profile.role not in ("MODERATOR", "SUPERADMIN"):
        if profile.admin_school_id != suggestion.school_id:
            return Response(
                {"detail": "You can only approve suggestions for your own school."},
                status=status.HTTP_403_FORBIDDEN,
            )

    result = approve_suggestion(suggestion, profile)
    return Response(SuggestionListSerializer(result).data)


@api_view(["POST"])
@permission_classes([IsProfileAuthenticated])
def reject_suggestion_view(request, pk):
    suggestion = get_object_or_404(Suggestion, pk=pk, status=Suggestion.Status.PENDING)
    profile = request.user_profile

    if profile.role not in ("MODERATOR", "SUPERADMIN"):
        if profile.admin_school_id != suggestion.school_id:
            return Response(
                {"detail": "You can only reject suggestions for your own school."},
                status=status.HTTP_403_FORBIDDEN,
            )

    reason = request.data.get("reason", "")
    result = reject_suggestion(suggestion, profile, reason)
    return Response(SuggestionListSerializer(result).data)


@api_view(["GET"])
def suggestion_image_view(request, pk):
    """Serve a suggestion's uploaded image as PNG."""
    suggestion = get_object_or_404(Suggestion, pk=pk)
    if not suggestion.image:
        return Response(status=status.HTTP_404_NOT_FOUND)
    from django.http import HttpResponse
    return HttpResponse(bytes(suggestion.image), content_type="image/png")
```

**Step 3: Update URLs**

`backend/community/api/urls.py`:
```python
from django.urls import path

from community.api.views import (
    approve_suggestion_view,
    pending_suggestions_view,
    reject_suggestion_view,
    school_suggestions_view,
    suggestion_image_view,
)

urlpatterns = [
    path(
        "schools/<str:moe_code>/suggestions/",
        school_suggestions_view,
        name="school-suggestions",
    ),
    path(
        "suggestions/pending/",
        pending_suggestions_view,
        name="suggestions-pending",
    ),
    path(
        "suggestions/<int:pk>/approve/",
        approve_suggestion_view,
        name="suggestion-approve",
    ),
    path(
        "suggestions/<int:pk>/reject/",
        reject_suggestion_view,
        name="suggestion-reject",
    ),
    path(
        "suggestions/<int:pk>/image/",
        suggestion_image_view,
        name="suggestion-image",
    ),
]
```

**Step 4: Write approval tests**

`backend/community/tests/test_approval.py`:
```python
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from community.models import Suggestion
from community.services import approve_suggestion, reject_suggestion
from outreach.models import SchoolImage
from schools.models import Constituency, School


class ApprovalServiceTest(TestCase):
    def setUp(self):
        self.constituency = Constituency.objects.create(
            code="P001", name="Test", state="Selangor"
        )
        self.school = School.objects.create(
            moe_code="ABC1234", name="SJK(T) Test", short_name="SJK(T) Test",
            constituency=self.constituency, state="Selangor", phone="03-1234567",
        )
        self.user = User.objects.create_user("testuser")
        self.profile = UserProfile.objects.create(
            user=self.user, google_id="google-123", display_name="Test User",
        )
        self.mod_user = User.objects.create_user("moduser")
        self.moderator = UserProfile.objects.create(
            user=self.mod_user, google_id="google-mod", display_name="Mod",
            role="MODERATOR",
        )

    def test_approve_data_correction_applies_change(self):
        s = Suggestion.objects.create(
            school=self.school, user=self.profile,
            type="DATA_CORRECTION", field_name="phone",
            current_value="03-1234567", suggested_value="03-9999999",
        )
        approve_suggestion(s, self.moderator)
        self.school.refresh_from_db()
        self.assertEqual(self.school.phone, "03-9999999")
        self.assertEqual(s.status, "APPROVED")
        self.assertEqual(s.points_awarded, 2)

    def test_approve_awards_points_to_user(self):
        s = Suggestion.objects.create(
            school=self.school, user=self.profile,
            type="NOTE", note="School relocated",
        )
        approve_suggestion(s, self.moderator)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.points, 1)

    def test_approve_photo_creates_school_image(self):
        s = Suggestion.objects.create(
            school=self.school, user=self.profile,
            type="PHOTO_UPLOAD", image=b"fake-png",
        )
        approve_suggestion(s, self.moderator)
        self.assertEqual(SchoolImage.objects.filter(school=self.school).count(), 1)
        img = SchoolImage.objects.get(school=self.school)
        self.assertEqual(img.source, "COMMUNITY")
        self.assertEqual(img.uploaded_by, self.profile)

    def test_reject_sets_reason(self):
        s = Suggestion.objects.create(
            school=self.school, user=self.profile,
            type="NOTE", note="test",
        )
        reject_suggestion(s, self.moderator, "Not relevant")
        self.assertEqual(s.status, "REJECTED")
        self.assertEqual(s.review_note, "Not relevant")
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.points, 0)

    def test_no_points_for_own_school(self):
        self.profile.admin_school = self.school
        self.profile.save()
        s = Suggestion.objects.create(
            school=self.school, user=self.profile,
            type="NOTE", note="test",
        )
        approve_suggestion(s, self.moderator)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.points, 0)
        self.assertEqual(s.points_awarded, 0)

    def test_max_10_images_per_school(self):
        for i in range(10):
            SchoolImage.objects.create(
                school=self.school, image_url=f"https://example.com/{i}.jpg",
                source="PLACES",
            )
        s = Suggestion.objects.create(
            school=self.school, user=self.profile,
            type="PHOTO_UPLOAD", image=b"fake-png",
        )
        approve_suggestion(s, self.moderator)
        self.assertEqual(SchoolImage.objects.filter(school=self.school).count(), 10)


class ModerationAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.constituency = Constituency.objects.create(
            code="P001", name="Test", state="Selangor"
        )
        self.school = School.objects.create(
            moe_code="ABC1234", name="SJK(T) Test", short_name="SJK(T) Test",
            constituency=self.constituency, state="Selangor",
        )
        self.user = User.objects.create_user("testuser")
        self.profile = UserProfile.objects.create(
            user=self.user, google_id="google-123", display_name="Test User",
        )
        self.mod_user = User.objects.create_user("moduser")
        self.moderator = UserProfile.objects.create(
            user=self.mod_user, google_id="google-mod", display_name="Mod",
            role="MODERATOR",
        )

    def _auth(self, profile):
        session = self.client.session
        session["user_profile_id"] = profile.pk
        session.save()

    def test_pending_queue_requires_moderator(self):
        self._auth(self.profile)
        resp = self.client.get("/api/v1/suggestions/pending/")
        self.assertEqual(resp.status_code, 403)

    def test_pending_queue_works_for_moderator(self):
        self._auth(self.moderator)
        Suggestion.objects.create(
            school=self.school, user=self.profile, type="NOTE", note="test",
        )
        resp = self.client.get("/api/v1/suggestions/pending/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)

    def test_approve_via_api(self):
        self._auth(self.moderator)
        s = Suggestion.objects.create(
            school=self.school, user=self.profile, type="NOTE", note="test",
        )
        resp = self.client.post(f"/api/v1/suggestions/{s.pk}/approve/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["status"], "APPROVED")

    def test_reject_via_api(self):
        self._auth(self.moderator)
        s = Suggestion.objects.create(
            school=self.school, user=self.profile, type="NOTE", note="test",
        )
        resp = self.client.post(
            f"/api/v1/suggestions/{s.pk}/reject/",
            {"reason": "Not useful"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["status"], "REJECTED")

    def test_regular_user_cannot_approve(self):
        self._auth(self.profile)
        s = Suggestion.objects.create(
            school=self.school, user=self.profile, type="NOTE", note="test",
        )
        resp = self.client.post(f"/api/v1/suggestions/{s.pk}/approve/")
        self.assertEqual(resp.status_code, 403)
```

**Step 5: Run tests**

```bash
python -m pytest community/ -v
```

Expected: ~22 tests PASS.

**Step 6: Commit**

```bash
git add backend/community/
git commit -m "feat: suggestion approval service and moderation API"
```

---

### Task 5: School Admin Image Management API

**Files:**
- Modify: `backend/community/api/views.py`
- Modify: `backend/community/api/urls.py`
- Test: `backend/community/tests/test_images.py`

**Step 1: Write image management views**

Add to `backend/community/api/views.py`:
```python
from outreach.models import SchoolImage


@api_view(["GET"])
def school_images_view(request, moe_code):
    """List images for a school, ordered by position."""
    school = get_object_or_404(School, moe_code=moe_code)
    images = SchoolImage.objects.filter(school=school)
    data = [
        {
            "id": img.pk,
            "image_url": img.image_url,
            "source": img.source,
            "position": img.position,
            "is_primary": img.is_primary,
            "attribution": img.attribution,
        }
        for img in images
    ]
    return Response(data)


@api_view(["PUT"])
@permission_classes([IsProfileAuthenticated])
def reorder_images_view(request, moe_code):
    """Reorder images. Body: {"order": [id1, id2, id3]}"""
    school = get_object_or_404(School, moe_code=moe_code)
    profile = request.user_profile

    if profile.role != "SUPERADMIN" and profile.admin_school_id != school.moe_code:
        return Response(
            {"detail": "Only school admin or superadmin can reorder images."},
            status=status.HTTP_403_FORBIDDEN,
        )

    order = request.data.get("order", [])
    for position, image_id in enumerate(order):
        SchoolImage.objects.filter(pk=image_id, school=school).update(position=position)

    return Response({"detail": "Images reordered."})


@api_view(["DELETE"])
@permission_classes([IsProfileAuthenticated])
def delete_image_view(request, moe_code, image_id):
    """Delete a school image."""
    school = get_object_or_404(School, moe_code=moe_code)
    profile = request.user_profile

    if profile.role != "SUPERADMIN" and profile.admin_school_id != school.moe_code:
        return Response(
            {"detail": "Only school admin or superadmin can delete images."},
            status=status.HTTP_403_FORBIDDEN,
        )

    image = get_object_or_404(SchoolImage, pk=image_id, school=school)
    image.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
```

**Step 2: Add URLs**

Add to `backend/community/api/urls.py`:
```python
path("schools/<str:moe_code>/images/", school_images_view, name="school-images"),
path("schools/<str:moe_code>/images/reorder/", reorder_images_view, name="reorder-images"),
path("schools/<str:moe_code>/images/<int:image_id>/", delete_image_view, name="delete-image"),
```

**Step 3: Write tests**

`backend/community/tests/test_images.py` — test reorder, delete, permissions.

**Step 4: Run tests and commit**

```bash
python -m pytest community/ -v
git add backend/community/
git commit -m "feat: school admin image management API"
```

---

### Task 6: Frontend — Suggest Form on School Page

**Files:**
- Create: `frontend/components/SuggestButton.tsx`
- Create: `frontend/components/SuggestForm.tsx`
- Modify: `frontend/app/[locale]/school/[moe_code]/page.tsx`
- Modify: `frontend/lib/api.ts` — add suggestion API functions
- Modify: `frontend/lib/types.ts` — add Suggestion type
- Modify: `frontend/messages/en.json`, `ta.json`, `ms.json` — add i18n strings

**Step 1: Add types and API client**

In `frontend/lib/types.ts`:
```typescript
export interface Suggestion {
  id: number;
  school: string;
  user_name: string;
  school_name: string;
  type: "DATA_CORRECTION" | "PHOTO_UPLOAD" | "NOTE";
  status: "PENDING" | "APPROVED" | "REJECTED";
  field_name: string;
  current_value: string;
  suggested_value: string;
  note: string;
  reviewed_by_name: string | null;
  review_note: string;
  points_awarded: number;
  created_at: string;
}
```

In `frontend/lib/api.ts` add:
```typescript
export async function createSuggestion(moeCode: string, data: object) { ... }
export async function fetchSuggestions(moeCode: string) { ... }
```

**Step 2: Build SuggestButton + SuggestForm**

- `SuggestButton`: shows "Suggest an edit" button on school page (only if signed in + not own school)
- `SuggestForm`: modal/slide-over with:
  - Type selector (Data Correction / Photo Upload / Note)
  - Field picker dropdown (for data corrections)
  - Value input or textarea
  - Image upload (for photos, max 3, client-side resize)
  - Submit button

**Step 3: Wire into school page**

Add `<SuggestButton moeCode={school.moe_code} />` to the school page sidebar, below EditSchoolLink.

**Step 4: Add i18n strings**

Add `suggestions` namespace to all 3 language files.

**Step 5: Write frontend tests and commit**

```bash
cd frontend && npm test -- --testPathPattern=Suggest
git add frontend/
git commit -m "feat: suggest form on school pages"
```

---

### Task 7: Frontend — My Suggestions on Profile + Moderation Queue on Dashboard

**Files:**
- Create: `frontend/components/MySuggestions.tsx`
- Create: `frontend/components/ModerationQueue.tsx`
- Create: `frontend/app/[locale]/dashboard/suggestions/page.tsx`
- Modify: `frontend/app/[locale]/profile/page.tsx` — add MySuggestions section
- Modify: `frontend/app/[locale]/dashboard/page.tsx` — add link to moderation queue
- Modify: `frontend/lib/api.ts` — add pending/approve/reject API functions

**Step 1: MySuggestions component**

- Fetches user's suggestions via `/api/v1/schools/<code>/suggestions/`
- Shows list with status badges (green=approved, yellow=pending, red=rejected)
- Rejected ones show review_note

**Step 2: ModerationQueue component**

- `/dashboard/suggestions` page (moderator+ only)
- Table: school, type, field, current→suggested, submitted by, date
- Approve/Reject buttons with confirmation
- Side-by-side diff for data corrections
- Image preview for photo uploads

**Step 3: Dashboard link**

Update dashboard cards to link to `/dashboard/suggestions` for moderator/school admin roles.

**Step 4: Add i18n, write tests, commit**

```bash
cd frontend && npm test
git add frontend/
git commit -m "feat: my suggestions + moderation queue frontend"
```

---

### Task 8: Frontend — School Admin Image Manager

**Files:**
- Create: `frontend/components/ImageManager.tsx`
- Create: `frontend/app/[locale]/dashboard/images/page.tsx`
- Modify: `frontend/lib/api.ts` — add image management API functions
- Modify: `frontend/app/[locale]/dashboard/page.tsx` — add link

**Step 1: ImageManager component**

- Grid of school images with drag handles (or up/down arrows for simplicity)
- Delete button (with confirmation) on each image
- Upload new image button
- Save order button → calls reorder API
- Max 10 images indicator

**Step 2: Dashboard link for school admins**

**Step 3: Tests and commit**

```bash
cd frontend && npm test
git add frontend/
git commit -m "feat: school admin image manager"
```

---

### Task 9: Deploy + Test + Sprint Close

**Step 1: Run full test suite**

```bash
cd backend && python -m pytest --tb=short
cd frontend && npm test
```

**Step 2: Deploy backend**

```bash
cd backend && gcloud run deploy sjktconnect-api --account admin@tamilfoundation.org --project sjktconnect --source . --region asia-southeast1 --allow-unauthenticated
```

**Step 3: Deploy frontend**

```bash
cd frontend && gcloud run deploy sjktconnect-web --account admin@tamilfoundation.org --project sjktconnect --source . --region asia-southeast1 --allow-unauthenticated
```

**Step 4: End-to-end test on production**

1. Sign in with Google on tamilschool.org
2. Go to a school page → click "Suggest an edit"
3. Submit a data correction, a note, and a photo
4. Check profile page → my suggestions shows 3 pending
5. Sign in as moderator → dashboard → moderation queue
6. Approve one, reject one → verify changes applied

**Step 5: Update CHANGELOG.md, CLAUDE.md, commit and push**

```bash
git add -A && git commit -m "docs: Sprint 8.2 close — suggestion workflow"
git push
```
