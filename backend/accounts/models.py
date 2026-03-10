import uuid

from django.db import models
from django.utils import timezone

from schools.models import School


class SchoolContact(models.Model):
    """A verified school representative who claimed their school page."""

    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name="contacts"
    )
    email = models.EmailField(db_index=True)
    name = models.CharField(max_length=200, blank=True, default="")
    role = models.CharField(
        max_length=100, blank=True, default="",
        help_text="e.g. Headmaster, Senior Assistant, Clerk",
    )
    is_active = models.BooleanField(default=True)
    verified_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("school", "email")]
        ordering = ["-verified_at"]

    def __str__(self):
        return f"{self.email} ({self.school.short_name})"


class MagicLinkToken(models.Model):
    """One-time token for passwordless authentication via email."""

    TOKEN_EXPIRY_HOURS = 24

    token = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    email = models.EmailField()
    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name="magic_tokens"
    )
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Token for {self.email} ({self.school.moe_code})"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        return not self.is_used and not self.is_expired


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
