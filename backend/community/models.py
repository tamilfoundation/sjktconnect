import uuid

from django.db import models


def _pending_upload_to(instance, filename):
    """Pending uploads live under an unguessable UUID path until approved.

    Supabase bucket is public-read; using UUIDs (32 hex chars) makes the URL
    unenumerable so a moderator-only image can't be discovered by guessing.
    On approval, bytes are copied into a SchoolImage row under
    schools/<moe>/<filename>; the original pending file is deleted.
    """
    ext = (filename.rsplit(".", 1)[-1] if "." in filename else "jpg").lower()
    return f"pending/{uuid.uuid4().hex}.{ext}"


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
    pending_image = models.ImageField(
        upload_to=_pending_upload_to, blank=True, null=True,
        help_text="Validated bytes for PHOTO_UPLOAD (Supabase Storage). "
                  "Cleared on approve (copied to SchoolImage) or reject.",
    )
    phash = models.CharField(
        max_length=32, blank=True, default="", db_index=True,
        help_text="Perceptual hash for dedup. Computed at upload time.",
    )
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
