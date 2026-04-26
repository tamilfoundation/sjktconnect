import logging

from django.utils import timezone
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import permission_classes as permission_classes_decorator
from django.db.models import Q
from django.shortcuts import get_object_or_404

from accounts.models import UserProfile
from accounts.permissions import IsProfileAuthenticated, IsSuperAdmin
from accounts.services.google import verify_google_token
from rest_framework.permissions import AllowAny
from schools.models import School

from .serializers import (
    GoogleAuthSerializer,
    UserProfileAdminListSerializer,
    UserProfileAdminUpdateSerializer,
    UserProfileSerializer,
    UserProfileUpdateSerializer,
)

logger = logging.getLogger(__name__)


def _maybe_auto_claim(profile, email):
    """If the Google account is a school's @moe.edu.my inbox, auto-bind admin_school.

    Idempotent: only sets admin_school if it's currently unset AND the school
    isn't already claimed by a different profile.
    """
    if profile.admin_school_id:
        return  # Already has a school

    email_lower = email.lower()
    if not email_lower.endswith("@moe.edu.my"):
        return

    moe_code = email_lower.split("@")[0].upper()
    try:
        school = School.objects.get(moe_code=moe_code, is_active=True)
    except School.DoesNotExist:
        return

    # Don't overwrite an existing claim — one school, one admin
    if UserProfile.objects.filter(admin_school=school).exclude(id=profile.id).exists():
        logger.warning(
            "Auto-claim skipped: school %s already claimed by another user (attempted by %s)",
            school.moe_code, email,
        )
        return

    profile.admin_school = school
    profile.save(update_fields=["admin_school", "updated_at"])

    if school.claimed_at is None:
        school.claimed_at = timezone.now()
        school.save(update_fields=["claimed_at", "updated_at"])

    logger.info("Auto-claim: %s -> school %s", email, school.moe_code)


class LogoutView(APIView):
    """Clear the Django session so fetchMe() returns null.

    Sprint 15 hotfix: NextAuth's signOut() only clears the frontend JWT.
    Without this endpoint the Django session cookie outlives the sign-out
    and `fetchMe()` keeps returning the user, leaving admin-only UI
    (EditSchoolLink etc.) visible. Frontend UserMenu.signOut() now calls
    this endpoint as part of its sign-out flow.

    Idempotent — calling on a session that's already empty returns 204.
    AllowAny so a stale session can sign itself out without authenticating.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        request.session.flush()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    """GET + PATCH the current user's profile.

    Only supports Google OAuth session (user_profile_id in Django session).
    Magic-link auth has been removed — see docs/tech-debt.md TD-02 resolution.

    PATCH lets the user update their own display_name.
    """

    def _get_profile(self, request):
        profile_id = request.session.get("user_profile_id")
        if not profile_id:
            return None
        try:
            return UserProfile.objects.select_related(
                "admin_school", "user",
            ).get(id=profile_id, is_active=True)
        except UserProfile.DoesNotExist:
            return None

    def get(self, request):
        profile = self._get_profile(request)
        if profile is None:
            return Response(
                {"detail": "Not authenticated"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return Response(UserProfileSerializer(profile).data)

    def patch(self, request):
        profile = self._get_profile(request)
        if profile is None:
            return Response(
                {"detail": "Not authenticated"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        serializer = UserProfileUpdateSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserProfileSerializer(profile).data)




class GoogleAuthView(APIView):
    """Authenticate with Google ID token. Creates or returns UserProfile.

    If the email is a school's @moe.edu.my Google Workspace account, auto-binds
    admin_school on first sign-in so the user immediately sees school-admin UI.
    """

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
            profile.display_name = google_info["name"]
            profile.avatar_url = google_info["picture"]
            profile.save(update_fields=["display_name", "avatar_url", "updated_at"])
        except UserProfile.DoesNotExist:
            from django.contrib.auth.models import User
            email = google_info["email"]
            username = email.split("@")[0][:150]
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

        # Auto-claim if this is an @moe.edu.my inbox for a real school
        _maybe_auto_claim(profile, google_info["email"])

        # Set session
        request.session["user_profile_id"] = profile.id

        # Reload to pick up admin_school if just-claimed
        profile = UserProfile.objects.select_related("admin_school").get(id=profile.id)
        return Response(UserProfileSerializer(profile).data)


# --- SUPERADMIN user management ---

class AdminUserListView(ListAPIView):
    """GET /api/v1/auth/admin/users/ — paginated list of UserProfiles.

    SUPERADMIN only. Filters:
      ?role=SUPERADMIN|MODERATOR|USER
      ?has_admin_school=true|false
      ?search=<substring> (matches display_name, email, admin_school.moe_code, admin_school.short_name)
      ?is_active=true|false
    """

    permission_classes = [IsProfileAuthenticated, IsSuperAdmin]
    serializer_class = UserProfileAdminListSerializer

    def get_queryset(self):
        qs = UserProfile.objects.select_related("user", "admin_school").all()

        role = self.request.query_params.get("role")
        if role:
            qs = qs.filter(role=role)

        has_admin_school = self.request.query_params.get("has_admin_school")
        if has_admin_school == "true":
            qs = qs.filter(admin_school__isnull=False)
        elif has_admin_school == "false":
            qs = qs.filter(admin_school__isnull=True)

        is_active = self.request.query_params.get("is_active")
        if is_active == "true":
            qs = qs.filter(is_active=True)
        elif is_active == "false":
            qs = qs.filter(is_active=False)

        search = self.request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(display_name__icontains=search)
                | Q(user__email__icontains=search)
                | Q(admin_school__moe_code__icontains=search)
                | Q(admin_school__short_name__icontains=search)
            )

        return qs.order_by("-updated_at")


class AdminUserDetailView(APIView):
    """PATCH /api/v1/auth/admin/users/<id>/ — update role / admin_school / is_active.
    DELETE — soft-delete (sets is_active=False).

    SUPERADMIN only. Prevents self-demotion: a SUPERADMIN cannot change their
    own role away from SUPERADMIN or set their own is_active=False.
    """

    permission_classes = [IsProfileAuthenticated, IsSuperAdmin]

    def _check_not_self_demote(self, request, target, validated):
        """Return an error Response if this would self-demote, else None."""
        if target.id != request.user_profile.id:
            return None

        new_role = validated.get("role")
        if new_role is not None and new_role != "SUPERADMIN":
            return Response(
                {"detail": "You cannot change your own role away from SUPERADMIN."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if validated.get("is_active") is False:
            return Response(
                {"detail": "You cannot deactivate your own account."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return None

    def patch(self, request, pk):
        target = get_object_or_404(UserProfile, pk=pk)
        serializer = UserProfileAdminUpdateSerializer(target, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        self_error = self._check_not_self_demote(request, target, serializer.validated_data)
        if self_error:
            return self_error

        serializer.save()
        target.refresh_from_db()
        return Response(UserProfileAdminListSerializer(target).data)

    def delete(self, request, pk):
        target = get_object_or_404(UserProfile, pk=pk)
        if target.id == request.user_profile.id:
            return Response(
                {"detail": "You cannot deactivate your own account."},
                status=status.HTTP_403_FORBIDDEN,
            )
        target.is_active = False
        target.save(update_fields=["is_active", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)
