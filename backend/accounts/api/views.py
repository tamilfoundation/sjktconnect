import logging

from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import UserProfile
from accounts.services.google import verify_google_token
from schools.models import School

from .serializers import (
    GoogleAuthSerializer,
    UserProfileSerializer,
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


class MeView(APIView):
    """Return the current user's profile.

    Only supports Google OAuth session (user_profile_id in Django session).
    Magic-link auth has been removed — see docs/tech-debt.md TD-02 resolution.
    """

    def get(self, request):
        profile_id = request.session.get("user_profile_id")
        if not profile_id:
            return Response(
                {"detail": "Not authenticated"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            profile = UserProfile.objects.select_related(
                "admin_school", "user",
            ).get(id=profile_id, is_active=True)
        except UserProfile.DoesNotExist:
            return Response(
                {"detail": "Not authenticated"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
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
