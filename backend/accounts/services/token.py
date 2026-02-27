"""Token generation and validation for Magic Link authentication."""

import logging
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.utils import timezone

from accounts.models import MagicLinkToken
from schools.models import School

logger = logging.getLogger(__name__)

MOE_EMAIL_DOMAIN = "moe.edu.my"


def validate_moe_email(email: str) -> bool:
    """Check that the email ends with @moe.edu.my."""
    return email.lower().strip().endswith(f"@{MOE_EMAIL_DOMAIN}")


def find_school_by_email(email: str) -> School | None:
    """Match an email to a school.

    MOE school emails follow the pattern [MOE_CODE]@moe.edu.my.
    Also checks the school's stored email field.
    """
    email_lower = email.lower().strip()
    local_part = email_lower.split("@")[0]

    # Try matching by MOE code (case-insensitive)
    school = School.objects.filter(moe_code__iexact=local_part).first()
    if school:
        return school

    # Try matching by stored email
    school = School.objects.filter(email__iexact=email_lower).first()
    if school:
        return school

    return None


def create_magic_token(email: str, school: School) -> MagicLinkToken:
    """Create a new magic link token for the given email and school."""
    expires_at = timezone.now() + timedelta(hours=MagicLinkToken.TOKEN_EXPIRY_HOURS)
    token = MagicLinkToken.objects.create(
        email=email.lower().strip(),
        school=school,
        expires_at=expires_at,
    )
    logger.info("Magic link token created for %s (school %s)", email, school.moe_code)
    return token


def verify_token(token_str: str) -> MagicLinkToken | None:
    """Validate and consume a magic link token.

    Returns the token if valid, None otherwise.
    Marks the token as used on success.
    """
    try:
        token = MagicLinkToken.objects.select_related("school").get(token=token_str)
    except (MagicLinkToken.DoesNotExist, ValueError, ValidationError):
        return None

    if not token.is_valid:
        return None

    token.is_used = True
    token.used_at = timezone.now()
    token.save(update_fields=["is_used", "used_at"])

    logger.info("Magic link token verified for %s (school %s)", token.email, token.school.moe_code)
    return token
