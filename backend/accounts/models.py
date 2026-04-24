from django.db import models


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
