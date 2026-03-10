import logging

from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import MagicLinkToken, SchoolContact, UserProfile
from accounts.services.email import send_magic_link_email
from accounts.services.google import verify_google_token
from accounts.services.token import (
    create_magic_token,
    find_school_by_email,
    validate_moe_email,
    verify_token,
)

from .serializers import (
    GoogleAuthSerializer,
    RequestMagicLinkSerializer,
    SchoolContactSerializer,
    UserProfileSerializer,
    VerifyTokenSerializer,
)

logger = logging.getLogger(__name__)


class RequestMagicLinkView(APIView):
    """POST /api/v1/auth/request-magic-link/

    Accepts an @moe.edu.my email, matches to a school,
    generates a magic link token, and sends the email.
    """

    def post(self, request):
        serializer = RequestMagicLinkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        if not validate_moe_email(email):
            return Response(
                {"error": "Only @moe.edu.my email addresses are accepted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        school = find_school_by_email(email)
        if not school:
            return Response(
                {"error": "No school found matching this email address."},
                status=status.HTTP_404_NOT_FOUND,
            )

        token = create_magic_token(email, school)
        send_magic_link_email(email, str(token.token), school.short_name)

        return Response(
            {
                "message": "Magic link sent. Please check your email.",
                "school_name": school.short_name,
            },
            status=status.HTTP_200_OK,
        )


class VerifyTokenView(APIView):
    """GET /api/v1/auth/verify/{token}/

    Validates the token, creates/updates SchoolContact,
    stores the session.
    """

    def get(self, request, token):
        magic_token = verify_token(token)
        if not magic_token:
            return Response(
                {"error": "Invalid or expired token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create or update SchoolContact
        contact, _created = SchoolContact.objects.update_or_create(
            school=magic_token.school,
            email=magic_token.email,
            defaults={"is_active": True},
        )

        # Store in session
        request.session["school_contact_id"] = contact.id
        request.session["school_moe_code"] = magic_token.school.moe_code

        data = VerifyTokenSerializer(contact).data
        return Response(data, status=status.HTTP_200_OK)


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

        # Set session
        request.session["user_profile_id"] = profile.id

        return Response(UserProfileSerializer(profile).data)


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
