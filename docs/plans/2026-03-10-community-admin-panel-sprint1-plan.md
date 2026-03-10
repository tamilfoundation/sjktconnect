# Community Admin Panel — Sprint 1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Google sign-in, UserProfile model with roles, and an admin panel shell — the foundation for community-driven school data maintenance.

**Architecture:** NextAuth.js v5 handles Google OAuth on the frontend, sends the ID token to a new Django endpoint that creates/returns a UserProfile. Existing magic link flow stays unchanged but gains a "link to Google account" step. New DRF permission classes gate role-based access.

**Tech Stack:** NextAuth.js v5 (App Router), `google-auth-library` (Python, backend token verification), Django 5.x, Next.js 14

**Design doc:** `docs/plans/2026-03-10-community-admin-panel-design.md`

---

### Task 1: UserProfile Model

**Files:**
- Modify: `backend/accounts/models.py`
- Create: `backend/accounts/migrations/0002_userprofile.py` (auto-generated)
- Test: `backend/accounts/tests/test_models.py`

**Step 1: Write the failing tests**

Add to `backend/accounts/tests/test_models.py`:

```python
from django.test import TestCase
from django.contrib.auth.models import User
from django.db import IntegrityError
from accounts.models import UserProfile
from schools.models import School


class UserProfileModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("testuser", "test@example.com", "pass")
        self.school = School.objects.create(
            moe_code="ABC1234",
            name="Sekolah Jenis Kebangsaan (Tamil) Test",
            short_name="SJK(T) Test",
            state="Selangor",
            ppd="Petaling Perdana",
        )

    def test_create_basic_profile(self):
        profile = UserProfile.objects.create(
            user=self.user,
            google_id="google-123",
            display_name="Test User",
        )
        self.assertEqual(profile.role, "USER")
        self.assertEqual(profile.points, 0)
        self.assertIsNone(profile.admin_school)
        self.assertTrue(profile.is_active)

    def test_google_id_unique(self):
        UserProfile.objects.create(user=self.user, google_id="google-123")
        user2 = User.objects.create_user("testuser2", "test2@example.com", "pass")
        with self.assertRaises(IntegrityError):
            UserProfile.objects.create(user=user2, google_id="google-123")

    def test_admin_school_unique(self):
        UserProfile.objects.create(
            user=self.user, google_id="g1", admin_school=self.school,
        )
        user2 = User.objects.create_user("testuser2", "test2@example.com", "pass")
        with self.assertRaises(IntegrityError):
            UserProfile.objects.create(
                user=user2, google_id="g2", admin_school=self.school,
            )

    def test_admin_school_nullable(self):
        profile = UserProfile.objects.create(user=self.user, google_id="g1")
        self.assertIsNone(profile.admin_school)

    def test_is_school_admin_property(self):
        profile = UserProfile.objects.create(
            user=self.user, google_id="g1", admin_school=self.school,
        )
        self.assertTrue(profile.is_school_admin)

    def test_is_school_admin_false_when_no_school(self):
        profile = UserProfile.objects.create(user=self.user, google_id="g1")
        self.assertFalse(profile.is_school_admin)

    def test_str(self):
        profile = UserProfile.objects.create(
            user=self.user, google_id="g1", display_name="Test User",
        )
        self.assertIn("Test User", str(profile))

    def test_role_choices(self):
        profile = UserProfile.objects.create(
            user=self.user, google_id="g1", role="MODERATOR",
        )
        self.assertEqual(profile.role, "MODERATOR")
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python manage.py test accounts.tests.test_models -v2`
Expected: FAIL — `ImportError: cannot import name 'UserProfile'`

**Step 3: Write the model**

Add to `backend/accounts/models.py` after existing models:

```python
class UserProfile(models.Model):
    """Community user profile linked to Django User and optionally a school."""

    class Role(models.TextChoices):
        SUPERADMIN = "SUPERADMIN", "Super Admin"
        MODERATOR = "MODERATOR", "Moderator"
        USER = "USER", "User"

    user = models.OneToOneField(
        "auth.User", on_delete=models.CASCADE, related_name="profile",
    )
    google_id = models.CharField(max_length=255, unique=True)
    display_name = models.CharField(max_length=200, blank=True, default="")
    avatar_url = models.URLField(max_length=500, blank=True, default="")
    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.USER,
    )
    admin_school = models.OneToOneField(
        "schools.School",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admin_profile",
    )
    points = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "user profile"
        verbose_name_plural = "user profiles"

    def __str__(self):
        return f"{self.display_name or self.user.username} ({self.role})"

    @property
    def is_school_admin(self):
        return self.admin_school_id is not None
```

**Step 4: Make migration and run tests**

Run: `cd backend && python manage.py makemigrations accounts && python manage.py test accounts.tests.test_models -v2`
Expected: All 8 tests PASS

**Step 5: Register in admin**

Add to `backend/accounts/admin.py`:

```python
from accounts.models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ["display_name", "user", "role", "admin_school", "points", "is_active"]
    list_filter = ["role", "is_active"]
    search_fields = ["display_name", "user__email", "google_id"]
    raw_id_fields = ["user", "admin_school"]
```

**Step 6: Commit**

```bash
git add accounts/models.py accounts/admin.py accounts/migrations/ accounts/tests/
git commit -m "feat: add UserProfile model with roles and school admin link"
```

---

### Task 2: Google Auth Backend Endpoint

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/accounts/services/google.py`
- Modify: `backend/accounts/api/views.py`
- Modify: `backend/accounts/api/serializers.py`
- Modify: `backend/accounts/api/urls.py`
- Test: `backend/accounts/tests/test_google_auth.py`

**Step 1: Install google-auth library**

Run: `cd backend && pip install google-auth==2.38.0 && pip freeze | grep google-auth`

Add to `requirements.txt`:
```
google-auth>=2.38.0,<3.0
```

**Step 2: Write the failing tests**

Create `backend/accounts/tests/test_google_auth.py`:

```python
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from accounts.models import UserProfile


class GoogleAuthEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/auth/google/"

    @patch("accounts.services.google.verify_google_token")
    def test_new_user_created(self, mock_verify):
        mock_verify.return_value = {
            "sub": "google-abc-123",
            "email": "user@gmail.com",
            "name": "Test User",
            "picture": "https://lh3.googleusercontent.com/photo.jpg",
        }
        response = self.client.post(self.url, {"id_token": "fake-token"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["google_id"], "google-abc-123")
        self.assertEqual(response.data["display_name"], "Test User")
        self.assertEqual(response.data["role"], "USER")
        self.assertEqual(response.data["points"], 0)
        self.assertIsNone(response.data["admin_school"])
        # Django User also created
        self.assertTrue(User.objects.filter(email="user@gmail.com").exists())
        # Profile linked
        profile = UserProfile.objects.get(google_id="google-abc-123")
        self.assertEqual(profile.user.email, "user@gmail.com")

    @patch("accounts.services.google.verify_google_token")
    def test_existing_user_returns_profile(self, mock_verify):
        mock_verify.return_value = {
            "sub": "google-abc-123",
            "email": "user@gmail.com",
            "name": "Updated Name",
            "picture": "https://lh3.googleusercontent.com/new.jpg",
        }
        # First login
        self.client.post(self.url, {"id_token": "fake-token"})
        # Second login
        response = self.client.post(self.url, {"id_token": "fake-token"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(UserProfile.objects.count(), 1)
        # Name/avatar updated
        profile = UserProfile.objects.get(google_id="google-abc-123")
        self.assertEqual(profile.display_name, "Updated Name")

    @patch("accounts.services.google.verify_google_token")
    def test_invalid_token_returns_401(self, mock_verify):
        mock_verify.return_value = None
        response = self.client.post(self.url, {"id_token": "bad-token"})
        self.assertEqual(response.status_code, 401)

    def test_missing_token_returns_400(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 400)

    @patch("accounts.services.google.verify_google_token")
    def test_session_set_on_success(self, mock_verify):
        mock_verify.return_value = {
            "sub": "google-abc-123",
            "email": "user@gmail.com",
            "name": "Test",
            "picture": "",
        }
        response = self.client.post(self.url, {"id_token": "fake-token"})
        self.assertEqual(response.status_code, 200)
        # Session should contain user_profile_id
        self.assertIn("user_profile_id", self.client.session)
```

**Step 3: Run tests to verify they fail**

Run: `cd backend && python manage.py test accounts.tests.test_google_auth -v2`
Expected: FAIL — import errors / URL not found

**Step 4: Implement Google token verification service**

Create `backend/accounts/services/google.py`:

```python
"""Google ID token verification."""

import logging
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

logger = logging.getLogger(__name__)

# Accept tokens from Google Sign-In
_GOOGLE_CLIENT_IDS = None


def _get_client_ids():
    """Lazily load client IDs from settings."""
    global _GOOGLE_CLIENT_IDS
    if _GOOGLE_CLIENT_IDS is None:
        import os
        client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
        _GOOGLE_CLIENT_IDS = [client_id] if client_id else []
    return _GOOGLE_CLIENT_IDS


def verify_google_token(token: str) -> dict | None:
    """
    Verify a Google ID token and return user info.

    Returns dict with keys: sub, email, name, picture.
    Returns None if verification fails.
    """
    try:
        client_ids = _get_client_ids()
        if not client_ids:
            logger.error("GOOGLE_OAUTH_CLIENT_ID not configured")
            return None
        idinfo = id_token.verify_oauth2_token(
            token, google_requests.Request(), clock_skew_in_seconds=10,
        )
        # Verify the issuer
        if idinfo.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
            logger.warning("Invalid issuer: %s", idinfo.get("iss"))
            return None
        # Verify audience matches our client ID
        if idinfo.get("aud") not in client_ids:
            logger.warning("Token audience mismatch")
            return None
        return {
            "sub": idinfo["sub"],
            "email": idinfo.get("email", ""),
            "name": idinfo.get("name", ""),
            "picture": idinfo.get("picture", ""),
        }
    except Exception:
        logger.exception("Google token verification failed")
        return None
```

**Step 5: Implement the view and serializer**

Add to `backend/accounts/api/serializers.py`:

```python
from accounts.models import UserProfile


class GoogleAuthSerializer(serializers.Serializer):
    id_token = serializers.CharField()


class UserProfileSerializer(serializers.ModelSerializer):
    admin_school = serializers.SerializerMethodField()
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            "id", "google_id", "display_name", "avatar_url",
            "role", "admin_school", "points", "is_active",
            "email",
        ]
        read_only_fields = fields

    def get_admin_school(self, obj):
        if obj.admin_school:
            return {
                "moe_code": obj.admin_school.moe_code,
                "name": obj.admin_school.short_name,
            }
        return None
```

Add to `backend/accounts/api/views.py`:

```python
from accounts.models import UserProfile
from accounts.services.google import verify_google_token
from accounts.api.serializers import GoogleAuthSerializer, UserProfileSerializer


class GoogleAuthView(APIView):
    """Authenticate with Google ID token. Creates or returns UserProfile."""

    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "id_token is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token = serializer.validated_data["id_token"]
        google_info = verify_google_token(token)
        if not google_info:
            return Response(
                {"error": "Invalid Google token"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Get or create UserProfile
        try:
            profile = UserProfile.objects.get(google_id=google_info["sub"])
            # Update display name and avatar on each login
            profile.display_name = google_info["name"]
            profile.avatar_url = google_info["picture"]
            profile.save(update_fields=["display_name", "avatar_url", "updated_at"])
        except UserProfile.DoesNotExist:
            # Create Django User + UserProfile
            from django.contrib.auth.models import User
            email = google_info["email"]
            username = email.split("@")[0][:150]
            # Ensure unique username
            base = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base}{counter}"
                counter += 1
            user = User.objects.create_user(
                username=username,
                email=email,
            )
            profile = UserProfile.objects.create(
                user=user,
                google_id=google_info["sub"],
                display_name=google_info["name"],
                avatar_url=google_info["picture"],
            )

        # Set session
        request.session["user_profile_id"] = profile.id

        return Response(UserProfileSerializer(profile).data)
```

**Step 6: Wire up the URL**

Add to `backend/accounts/api/urls.py`:

```python
from accounts.api.views import GoogleAuthView

# Add to urlpatterns:
path("google/", GoogleAuthView.as_view(), name="google-auth"),
```

**Step 7: Run tests**

Run: `cd backend && python manage.py test accounts.tests.test_google_auth -v2`
Expected: All 5 tests PASS

**Step 8: Commit**

```bash
git add requirements.txt accounts/services/google.py accounts/api/ accounts/tests/
git commit -m "feat: add Google auth endpoint with token verification"
```

---

### Task 3: Update /me Endpoint for UserProfile

**Files:**
- Modify: `backend/accounts/api/views.py`
- Test: `backend/accounts/tests/test_me_endpoint.py`

**Step 1: Write the failing tests**

Create `backend/accounts/tests/test_me_endpoint.py`:

```python
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from accounts.models import UserProfile
from schools.models import School


class MeEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/auth/me/"

    def test_unauthenticated_returns_401(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)

    def test_google_session_returns_profile(self):
        user = User.objects.create_user("guser", "g@gmail.com", "pass")
        profile = UserProfile.objects.create(
            user=user, google_id="g-123", display_name="Google User",
        )
        session = self.client.session
        session["user_profile_id"] = profile.id
        session.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["display_name"], "Google User")
        self.assertEqual(response.data["role"], "USER")

    def test_magic_link_session_still_works(self):
        """Backward compatibility: existing magic link sessions still return data."""
        school = School.objects.create(
            moe_code="XYZ0001", name="Test School",
            short_name="SJK(T) Test", state="Selangor", ppd="Test",
        )
        from accounts.models import SchoolContact
        contact = SchoolContact.objects.create(
            school=school, email="test@moe.edu.my", is_active=True,
        )
        session = self.client.session
        session["school_contact_id"] = contact.id
        session["school_moe_code"] = school.moe_code
        session.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        # Returns legacy format
        self.assertEqual(response.data["school_moe_code"], "XYZ0001")

    def test_google_session_with_admin_school(self):
        school = School.objects.create(
            moe_code="XYZ0002", name="Admin School",
            short_name="SJK(T) Admin", state="Perak", ppd="Test",
        )
        user = User.objects.create_user("admin", "admin@moe.edu.my", "pass")
        profile = UserProfile.objects.create(
            user=user, google_id="g-admin", display_name="Admin",
            admin_school=school,
        )
        session = self.client.session
        session["user_profile_id"] = profile.id
        session.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["admin_school"]["moe_code"], "XYZ0002")
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python manage.py test accounts.tests.test_me_endpoint -v2`
Expected: FAIL — MeView doesn't check `user_profile_id` session

**Step 3: Update MeView to handle both session types**

Modify `MeView` in `backend/accounts/api/views.py`:

```python
class MeView(APIView):
    """Return the current user's profile.

    Checks for Google auth session first (user_profile_id),
    falls back to magic link session (school_contact_id) for
    backward compatibility.
    """

    def get(self, request):
        # Check Google auth session first
        profile_id = request.session.get("user_profile_id")
        if profile_id:
            try:
                profile = UserProfile.objects.select_related(
                    "admin_school", "user",
                ).get(id=profile_id, is_active=True)
                return Response(UserProfileSerializer(profile).data)
            except UserProfile.DoesNotExist:
                pass

        # Fall back to magic link session (backward compatibility)
        contact_id = request.session.get("school_contact_id")
        if contact_id:
            try:
                contact = SchoolContact.objects.select_related("school").get(
                    id=contact_id, is_active=True,
                )
                return Response(SchoolContactSerializer(contact).data)
            except SchoolContact.DoesNotExist:
                pass

        return Response(
            {"detail": "Not authenticated"},
            status=status.HTTP_401_UNAUTHORIZED,
        )
```

**Step 4: Run tests**

Run: `cd backend && python manage.py test accounts.tests.test_me_endpoint -v2`
Expected: All 4 tests PASS

**Step 5: Commit**

```bash
git add accounts/api/views.py accounts/tests/
git commit -m "feat: update /me endpoint to support Google auth sessions"
```

---

### Task 4: Link School to Google Account Endpoint

**Files:**
- Modify: `backend/accounts/api/views.py`
- Modify: `backend/accounts/api/urls.py`
- Test: `backend/accounts/tests/test_link_school.py`

**Step 1: Write the failing tests**

Create `backend/accounts/tests/test_link_school.py`:

```python
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from accounts.models import UserProfile, SchoolContact, MagicLinkToken
from schools.models import School
import uuid
from django.utils import timezone
from datetime import timedelta


class LinkSchoolTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/v1/auth/link-school/"
        self.school = School.objects.create(
            moe_code="ABC1234", name="Test School",
            short_name="SJK(T) Test", state="Selangor", ppd="Test",
        )
        self.user = User.objects.create_user("guser", "g@gmail.com", "pass")
        self.profile = UserProfile.objects.create(
            user=self.user, google_id="g-123", display_name="User",
        )
        # Create a valid magic link token
        self.token = MagicLinkToken.objects.create(
            token=uuid.uuid4(),
            email="abc1234@moe.edu.my",
            school=self.school,
            expires_at=timezone.now() + timedelta(hours=24),
        )

    def test_link_school_success(self):
        # Set Google session
        session = self.client.session
        session["user_profile_id"] = self.profile.id
        session.save()
        response = self.client.post(self.url, {"token": str(self.token.token)})
        self.assertEqual(response.status_code, 200)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.admin_school, self.school)

    def test_link_school_no_session_401(self):
        response = self.client.post(self.url, {"token": str(self.token.token)})
        self.assertEqual(response.status_code, 401)

    def test_link_school_invalid_token_400(self):
        session = self.client.session
        session["user_profile_id"] = self.profile.id
        session.save()
        response = self.client.post(self.url, {"token": str(uuid.uuid4())})
        self.assertEqual(response.status_code, 400)

    def test_link_school_already_claimed_409(self):
        # Another user already admins this school
        user2 = User.objects.create_user("other", "other@gmail.com", "pass")
        UserProfile.objects.create(
            user=user2, google_id="g-other", admin_school=self.school,
        )
        session = self.client.session
        session["user_profile_id"] = self.profile.id
        session.save()
        response = self.client.post(self.url, {"token": str(self.token.token)})
        self.assertEqual(response.status_code, 409)
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python manage.py test accounts.tests.test_link_school -v2`
Expected: FAIL — URL not found

**Step 3: Implement the view**

Add to `backend/accounts/api/views.py`:

```python
class LinkSchoolView(APIView):
    """Link a magic-link-verified school to the current Google profile."""

    def post(self, request):
        profile_id = request.session.get("user_profile_id")
        if not profile_id:
            return Response(
                {"error": "Sign in with Google first"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            profile = UserProfile.objects.get(id=profile_id, is_active=True)
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "Profile not found"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        token_str = request.data.get("token", "")
        try:
            token = MagicLinkToken.objects.get(
                token=token_str, is_used=False,
            )
        except MagicLinkToken.DoesNotExist:
            return Response(
                {"error": "Invalid or expired token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if token.is_expired:
            return Response(
                {"error": "Token has expired"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        school = token.school

        # Check if school is already claimed by another profile
        if UserProfile.objects.filter(admin_school=school).exclude(id=profile.id).exists():
            return Response(
                {"error": "This school is already claimed by another user"},
                status=status.HTTP_409_CONFLICT,
            )

        # Link school to profile
        profile.admin_school = school
        profile.save(update_fields=["admin_school", "updated_at"])

        # Mark token as used
        from django.utils import timezone
        token.is_used = True
        token.used_at = timezone.now()
        token.save(update_fields=["is_used", "used_at"])

        # Create/update SchoolContact for backward compatibility
        SchoolContact.objects.update_or_create(
            school=school,
            email=token.email,
            defaults={"is_active": True, "name": profile.display_name},
        )

        return Response(UserProfileSerializer(profile).data)
```

**Step 4: Wire up URL**

Add to `backend/accounts/api/urls.py`:

```python
from accounts.api.views import LinkSchoolView

# Add to urlpatterns:
path("link-school/", LinkSchoolView.as_view(), name="link-school"),
```

**Step 5: Run tests**

Run: `cd backend && python manage.py test accounts.tests.test_link_school -v2`
Expected: All 4 tests PASS

**Step 6: Commit**

```bash
git add accounts/api/views.py accounts/api/urls.py accounts/tests/
git commit -m "feat: add link-school endpoint to connect magic link to Google profile"
```

---

### Task 5: Role-Based Permission Classes

**Files:**
- Modify: `backend/accounts/permissions.py`
- Test: `backend/accounts/tests/test_permissions.py`

**Step 1: Write the failing tests**

Create `backend/accounts/tests/test_permissions.py`:

```python
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
        # Simulate a view with obj.school or obj == school
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
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python manage.py test accounts.tests.test_permissions -v2`
Expected: FAIL — cannot import new permission classes

**Step 3: Implement permission classes**

Add to `backend/accounts/permissions.py`:

```python
from accounts.models import UserProfile


class IsProfileAuthenticated(BasePermission):
    """Check that the request has a valid UserProfile session."""

    def has_permission(self, request, view):
        profile_id = request.session.get("user_profile_id")
        if not profile_id:
            return False
        try:
            profile = UserProfile.objects.select_related(
                "admin_school",
            ).get(id=profile_id, is_active=True)
            request.user_profile = profile
            return True
        except UserProfile.DoesNotExist:
            return False


class IsModeratorOrAbove(BasePermission):
    """Requires MODERATOR or SUPERADMIN role. Must be used after IsProfileAuthenticated."""

    def has_permission(self, request, view):
        profile = getattr(request, "user_profile", None)
        if not profile:
            return False
        return profile.role in ("MODERATOR", "SUPERADMIN")


class IsSuperAdmin(BasePermission):
    """Requires SUPERADMIN role. Must be used after IsProfileAuthenticated."""

    def has_permission(self, request, view):
        profile = getattr(request, "user_profile", None)
        if not profile:
            return False
        return profile.role == "SUPERADMIN"


class IsSchoolAdminForObject(BasePermission):
    """Check user is admin for the specific school object.

    Works with objects that ARE a School or have a .school FK.
    Must be used after IsProfileAuthenticated.
    """

    def has_object_permission(self, request, view, obj):
        profile = getattr(request, "user_profile", None)
        if not profile or not profile.admin_school_id:
            return False
        # Superadmin can access any school
        if profile.role == "SUPERADMIN":
            return True
        # Determine the school from the object
        from schools.models import School
        if isinstance(obj, School):
            school = obj
        elif hasattr(obj, "school"):
            school = obj.school
        else:
            return False
        return profile.admin_school_id == school.pk
```

**Step 4: Run tests**

Run: `cd backend && python manage.py test accounts.tests.test_permissions -v2`
Expected: All 8 tests PASS

**Step 5: Commit**

```bash
git add accounts/permissions.py accounts/tests/
git commit -m "feat: add role-based permission classes for community admin"
```

---

### Task 6: Frontend — Install NextAuth.js + Google Provider

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/app/api/auth/[...nextauth]/route.ts`
- Create: `frontend/lib/auth.ts`
- Create: `frontend/.env.local` (template — not committed)

**Step 1: Install NextAuth.js v5**

Run:
```bash
cd frontend && npm install next-auth@beta @auth/core
```

**Step 2: Create the auth configuration**

Create `frontend/lib/auth.ts`:

```typescript
import NextAuth from "next-auth";
import Google from "next-auth/providers/google";

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    Google({
      clientId: process.env.GOOGLE_OAUTH_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_OAUTH_CLIENT_SECRET!,
    }),
  ],
  callbacks: {
    async jwt({ token, account }) {
      // On initial sign-in, store the Google ID token
      if (account?.id_token) {
        token.id_token = account.id_token;
      }
      return token;
    },
    async session({ session, token }) {
      // Pass Google ID token to session for backend sync
      (session as any).id_token = token.id_token;
      return session;
    },
  },
  pages: {
    signIn: "/sign-in",
  },
});
```

**Step 3: Create the API route handler**

Create `frontend/app/api/auth/[...nextauth]/route.ts`:

```typescript
import { handlers } from "@/lib/auth";

export const { GET, POST } = handlers;
```

**Step 4: Add env vars template**

Document required env vars (do NOT commit actual values):

```
# Add to Cloud Run env vars:
# GOOGLE_OAUTH_CLIENT_ID=<from GCP Console>
# GOOGLE_OAUTH_CLIENT_SECRET=<from GCP Console>
# NEXTAUTH_SECRET=<random 32+ char string>
# NEXTAUTH_URL=https://tamilschool.org (or http://localhost:3000 for dev)
```

**Step 5: Commit**

```bash
git add frontend/lib/auth.ts frontend/app/api/auth/ frontend/package.json frontend/package-lock.json
git commit -m "feat: add NextAuth.js v5 with Google provider"
```

---

### Task 7: Frontend — Auth Provider + Backend Sync

**Files:**
- Create: `frontend/components/AuthProvider.tsx`
- Create: `frontend/lib/auth-api.ts`
- Modify: `frontend/app/[locale]/layout.tsx`
- Modify: `frontend/lib/types.ts`

**Step 1: Create auth API functions**

Create `frontend/lib/auth-api.ts`:

```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface UserProfile {
  id: number;
  google_id: string;
  display_name: string;
  avatar_url: string;
  role: "SUPERADMIN" | "MODERATOR" | "USER";
  admin_school: { moe_code: string; name: string } | null;
  points: number;
  is_active: boolean;
  email: string;
}

/** Send Google ID token to backend, get/create UserProfile */
export async function syncGoogleAuth(idToken: string): Promise<UserProfile> {
  const res = await fetch(`${API_URL}/api/v1/auth/google/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ id_token: idToken }),
  });
  if (!res.ok) throw new Error("Auth sync failed");
  return res.json();
}

/** Fetch current user profile from backend */
export async function fetchProfile(): Promise<UserProfile | null> {
  try {
    const res = await fetch(`${API_URL}/api/v1/auth/me/`, {
      credentials: "include",
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}
```

**Step 2: Create AuthProvider wrapper**

Create `frontend/components/AuthProvider.tsx`:

```typescript
"use client";

import { SessionProvider } from "next-auth/react";
import { ReactNode } from "react";

export default function AuthProvider({ children }: { children: ReactNode }) {
  return <SessionProvider>{children}</SessionProvider>;
}
```

**Step 3: Wrap layout with AuthProvider**

Modify `frontend/app/[locale]/layout.tsx` — wrap children with AuthProvider:

```typescript
import AuthProvider from "@/components/AuthProvider";

// In the return JSX, wrap NextIntlClientProvider contents:
<NextIntlClientProvider messages={messages}>
  <AuthProvider>
    <Header />
    <main id="main-content" className="flex-1">{children}</main>
    <Footer />
  </AuthProvider>
</NextIntlClientProvider>
```

**Step 4: Commit**

```bash
git add frontend/components/AuthProvider.tsx frontend/lib/auth-api.ts frontend/app/[locale]/layout.tsx
git commit -m "feat: add AuthProvider and backend sync for Google auth"
```

---

### Task 8: Frontend — Sign In/Out in Header

**Files:**
- Modify: `frontend/components/Header.tsx`
- Create: `frontend/components/UserMenu.tsx`
- Modify: `frontend/messages/en.json`
- Modify: `frontend/messages/ms.json`
- Modify: `frontend/messages/ta.json`

**Step 1: Create UserMenu component**

Create `frontend/components/UserMenu.tsx`:

```typescript
"use client";

import { useState, useRef, useEffect } from "react";
import { useSession, signIn, signOut } from "next-auth/react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { syncGoogleAuth, type UserProfile } from "@/lib/auth-api";

export default function UserMenu() {
  const t = useTranslations("auth");
  const { data: session, status } = useSession();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Sync with backend when session is available
  useEffect(() => {
    if (session && (session as any).id_token && !profile) {
      syncGoogleAuth((session as any).id_token)
        .then(setProfile)
        .catch(() => {});
    }
  }, [session, profile]);

  // Close on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  if (status === "loading") return null;

  if (!session) {
    return (
      <button
        onClick={() => signIn("google")}
        className="text-sm font-medium text-gray-700 hover:text-primary-600 transition-colors"
      >
        {t("signIn")}
      </button>
    );
  }

  const avatarUrl = profile?.avatar_url || session.user?.image || "";
  const displayName = profile?.display_name || session.user?.name || "";
  const role = profile?.role || "USER";

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 text-sm"
      >
        {avatarUrl ? (
          <img
            src={avatarUrl}
            alt=""
            className="w-8 h-8 rounded-full border border-gray-200"
            referrerPolicy="no-referrer"
          />
        ) : (
          <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center text-primary-700 font-medium">
            {displayName.charAt(0).toUpperCase()}
          </div>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-56 bg-white rounded-xl border border-gray-200 shadow-lg py-2 z-50">
          <div className="px-4 py-2 border-b border-gray-100">
            <p className="text-sm font-medium text-gray-900 truncate">{displayName}</p>
            <p className="text-xs text-gray-500">{t(`role_${role}`)}</p>
            {profile?.points !== undefined && profile.points > 0 && (
              <p className="text-xs text-primary-600 mt-0.5">
                {profile.points} {t("points")}
              </p>
            )}
          </div>
          <Link
            href="/profile"
            className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
            onClick={() => setOpen(false)}
          >
            {t("profile")}
          </Link>
          {(role === "MODERATOR" || role === "SUPERADMIN" || profile?.admin_school) && (
            <Link
              href="/dashboard"
              className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
              onClick={() => setOpen(false)}
            >
              {t("dashboard")}
            </Link>
          )}
          <button
            onClick={() => signOut()}
            className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-gray-50"
          >
            {t("signOut")}
          </button>
        </div>
      )}
    </div>
  );
}
```

**Step 2: Add UserMenu to Header**

In `frontend/components/Header.tsx`, import and add `<UserMenu />` next to the Subscribe/Donate buttons in the desktop nav area.

**Step 3: Add i18n strings**

Add `"auth"` namespace to all three message files:

```json
"auth": {
  "signIn": "Sign in",
  "signOut": "Sign out",
  "profile": "My Profile",
  "dashboard": "Dashboard",
  "points": "points",
  "role_USER": "Member",
  "role_MODERATOR": "Moderator",
  "role_SUPERADMIN": "Admin"
}
```

Tamil (`ta.json`):
```json
"auth": {
  "signIn": "உள்நுழையவும்",
  "signOut": "வெளியேறு",
  "profile": "என் சுயவிவரம்",
  "dashboard": "நிர்வாகம்",
  "points": "புள்ளிகள்",
  "role_USER": "உறுப்பினர்",
  "role_MODERATOR": "மதிப்பாளர்",
  "role_SUPERADMIN": "நிர்வாகி"
}
```

Malay (`ms.json`):
```json
"auth": {
  "signIn": "Log masuk",
  "signOut": "Log keluar",
  "profile": "Profil Saya",
  "dashboard": "Panel Kawalan",
  "points": "mata",
  "role_USER": "Ahli",
  "role_MODERATOR": "Moderator",
  "role_SUPERADMIN": "Pentadbir"
}
```

**Step 4: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

**Step 5: Commit**

```bash
git add frontend/components/UserMenu.tsx frontend/components/Header.tsx frontend/messages/
git commit -m "feat: add UserMenu with Google sign-in/out and role display"
```

---

### Task 9: Frontend — Profile Page

**Files:**
- Create: `frontend/app/[locale]/profile/page.tsx`

**Step 1: Create profile page**

Create `frontend/app/[locale]/profile/page.tsx`:

```typescript
"use client";

import { useSession } from "next-auth/react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { useEffect, useState } from "react";
import { fetchProfile, type UserProfile } from "@/lib/auth-api";

export default function ProfilePage() {
  const t = useTranslations("auth");
  const { data: session, status } = useSession();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProfile()
      .then(setProfile)
      .finally(() => setLoading(false));
  }, []);

  if (status === "loading" || loading) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center text-gray-500">
        Loading...
      </div>
    );
  }

  if (!session || !profile) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center">
        <p className="text-gray-600 mb-4">{t("signInRequired")}</p>
      </div>
    );
  }

  const roleBadgeColor = {
    SUPERADMIN: "bg-red-100 text-red-800",
    MODERATOR: "bg-purple-100 text-purple-800",
    USER: "bg-blue-100 text-blue-800",
  }[profile.role];

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8">
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        {/* Avatar + Name */}
        <div className="flex items-center gap-4 mb-6">
          {profile.avatar_url ? (
            <img
              src={profile.avatar_url}
              alt=""
              className="w-16 h-16 rounded-full border-2 border-gray-200"
              referrerPolicy="no-referrer"
            />
          ) : (
            <div className="w-16 h-16 rounded-full bg-primary-100 flex items-center justify-center text-2xl font-bold text-primary-700">
              {profile.display_name.charAt(0).toUpperCase()}
            </div>
          )}
          <div>
            <h1 className="text-xl font-bold text-gray-900">
              {profile.display_name}
            </h1>
            <p className="text-sm text-gray-500">{profile.email}</p>
            <span className={`inline-block mt-1 text-xs font-medium px-2 py-0.5 rounded-full ${roleBadgeColor}`}>
              {t(`role_${profile.role}`)}
            </span>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="bg-gray-50 rounded-lg p-4 text-center">
            <p className="text-2xl font-bold text-primary-600">{profile.points}</p>
            <p className="text-xs text-gray-500">{t("points")}</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-4 text-center">
            <p className="text-2xl font-bold text-primary-600">
              {profile.admin_school ? "1" : "0"}
            </p>
            <p className="text-xs text-gray-500">{t("schoolsManaged")}</p>
          </div>
        </div>

        {/* Admin School */}
        {profile.admin_school && (
          <div className="border border-primary-100 bg-primary-50 rounded-lg p-4 mb-6">
            <p className="text-xs text-primary-600 font-medium mb-1">
              {t("yourSchool")}
            </p>
            <Link
              href={`/school/${profile.admin_school.moe_code}`}
              className="text-base font-semibold text-primary-900 hover:text-primary-700"
            >
              {profile.admin_school.name}
            </Link>
          </div>
        )}

        {/* Claim school CTA if no admin school */}
        {!profile.admin_school && (
          <div className="border border-gray-200 rounded-lg p-4 text-center">
            <p className="text-sm text-gray-600 mb-2">
              {t("claimSchoolCta")}
            </p>
            <Link
              href="/claim"
              className="inline-block text-sm font-medium text-primary-600 hover:text-primary-700"
            >
              {t("claimSchool")} &rarr;
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
```

**Step 2: Add i18n strings**

Add to the `"auth"` namespace in all message files:

```json
"signInRequired": "Please sign in to view your profile.",
"schoolsManaged": "Schools managed",
"yourSchool": "Your school",
"claimSchoolCta": "Are you a school representative? Link your school to manage its data.",
"claimSchool": "Claim your school"
```

**Step 3: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

**Step 4: Commit**

```bash
git add frontend/app/[locale]/profile/ frontend/messages/
git commit -m "feat: add user profile page with role badge and school link"
```

---

### Task 10: Frontend — Dashboard Shell

**Files:**
- Create: `frontend/app/[locale]/dashboard/page.tsx`

**Step 1: Create dashboard shell**

Create `frontend/app/[locale]/dashboard/page.tsx`:

```typescript
"use client";

import { useSession } from "next-auth/react";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { fetchProfile, type UserProfile } from "@/lib/auth-api";

export default function DashboardPage() {
  const t = useTranslations("dashboard");
  const { status } = useSession();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProfile()
      .then(setProfile)
      .finally(() => setLoading(false));
  }, []);

  if (status === "loading" || loading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-16 text-center text-gray-500">
        Loading...
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-16 text-center text-gray-500">
        Please sign in to access the dashboard.
      </div>
    );
  }

  const isSuperAdmin = profile.role === "SUPERADMIN";
  const isModerator = profile.role === "MODERATOR" || isSuperAdmin;
  const isSchoolAdmin = !!profile.admin_school;

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">
        {t("heading")}
      </h1>
      <p className="text-sm text-gray-500 mb-8">
        {t("welcome", { name: profile.display_name })}
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* School Admin section */}
        {isSchoolAdmin && (
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h2 className="text-base font-semibold text-gray-900 mb-2">
              {t("mySchool")}
            </h2>
            <p className="text-sm text-gray-600 mb-3">
              {profile.admin_school!.name}
            </p>
            <p className="text-xs text-gray-400">{t("comingSoon")}</p>
          </div>
        )}

        {/* Moderation section */}
        {isModerator && (
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h2 className="text-base font-semibold text-gray-900 mb-2">
              {t("moderation")}
            </h2>
            <p className="text-xs text-gray-400">{t("comingSoon")}</p>
          </div>
        )}

        {/* Super Admin section */}
        {isSuperAdmin && (
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h2 className="text-base font-semibold text-gray-900 mb-2">
              {t("administration")}
            </h2>
            <p className="text-xs text-gray-400">{t("comingSoon")}</p>
          </div>
        )}

        {/* All users: contributions */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-base font-semibold text-gray-900 mb-2">
            {t("myContributions")}
          </h2>
          <p className="text-xs text-gray-400">{t("comingSoon")}</p>
        </div>
      </div>
    </div>
  );
}
```

**Step 2: Add i18n strings**

Add `"dashboard"` namespace to all message files:

English:
```json
"dashboard": {
  "heading": "Dashboard",
  "welcome": "Welcome, {name}",
  "mySchool": "My School",
  "moderation": "Moderation Queue",
  "administration": "Administration",
  "myContributions": "My Contributions",
  "comingSoon": "Coming soon — features will appear here as they are built."
}
```

Tamil:
```json
"dashboard": {
  "heading": "நிர்வாகப் பலகை",
  "welcome": "வணக்கம், {name}",
  "mySchool": "என் பள்ளி",
  "moderation": "மதிப்பாய்வு வரிசை",
  "administration": "நிர்வாகம்",
  "myContributions": "என் பங்களிப்புகள்",
  "comingSoon": "விரைவில் — அம்சங்கள் உருவாக்கப்படும்போது இங்கே தோன்றும்."
}
```

Malay:
```json
"dashboard": {
  "heading": "Panel Kawalan",
  "welcome": "Selamat datang, {name}",
  "mySchool": "Sekolah Saya",
  "moderation": "Barisan Moderasi",
  "administration": "Pentadbiran",
  "myContributions": "Sumbangan Saya",
  "comingSoon": "Akan datang — ciri-ciri akan muncul di sini apabila siap."
}
```

**Step 3: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

**Step 4: Commit**

```bash
git add frontend/app/[locale]/dashboard/ frontend/messages/
git commit -m "feat: add role-gated dashboard shell with placeholder sections"
```

---

### Task 11: Backend — Add GOOGLE_OAUTH_CLIENT_ID to Settings

**Files:**
- Modify: `backend/sjktconnect/settings/base.py`

**Step 1: Add env var to settings**

Add to `backend/sjktconnect/settings/base.py` near the other env vars:

```python
# Google OAuth (for community sign-in)
GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
```

**Step 2: Update CORS to allow credentials**

Verify `CORS_ALLOW_CREDENTIALS = True` is set (should already be there for magic link sessions).

**Step 3: Run full backend test suite**

Run: `cd backend && python manage.py test --keepdb -v0`
Expected: All tests pass (existing + new)

**Step 4: Run frontend build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

**Step 5: Final commit**

```bash
git add backend/sjktconnect/settings/base.py
git commit -m "feat: add GOOGLE_OAUTH_CLIENT_ID setting for community auth"
```

---

## Environment Setup Checklist (Pre-deployment)

Before deploying, these env vars need to be set:

**GCP Console — OAuth 2.0 Client:**
1. Go to APIs & Credentials in GCP project `sjktconnect`
2. Create OAuth 2.0 Client ID (Web application)
3. Authorised origins: `https://tamilschool.org`, `http://localhost:3000`
4. Authorised redirect URIs: `https://tamilschool.org/api/auth/callback/google`, `http://localhost:3000/api/auth/callback/google`

**Cloud Run — Backend (sjktconnect-api):**
- `GOOGLE_OAUTH_CLIENT_ID=<from step above>`

**Cloud Run — Frontend (sjktconnect-web):**
- `GOOGLE_OAUTH_CLIENT_ID=<same as backend>`
- `GOOGLE_OAUTH_CLIENT_SECRET=<from step above>`
- `NEXTAUTH_SECRET=<generate: openssl rand -base64 32>`
- `NEXTAUTH_URL=https://tamilschool.org`
