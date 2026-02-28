"""Models for school outreach: images and email campaigns."""

from django.db import models


class SchoolImage(models.Model):
    """Image associated with a school (satellite, Places API, or manual upload)."""

    class Source(models.TextChoices):
        SATELLITE = "SATELLITE", "Satellite (Google Static Maps)"
        STREET_VIEW = "STREET_VIEW", "Street View"
        PLACES = "PLACES", "Google Places"
        MANUAL = "MANUAL", "Manual Upload"

    school = models.ForeignKey(
        "schools.School", on_delete=models.CASCADE, related_name="images"
    )
    image_url = models.URLField(max_length=500)
    source = models.CharField(max_length=20, choices=Source.choices)
    is_primary = models.BooleanField(default=False)
    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)
    attribution = models.CharField(max_length=500, blank=True, default="")
    photo_reference = models.CharField(
        max_length=500, blank=True, default="",
        help_text="Google Places photo_reference for re-fetching.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_primary", "-created_at"]

    def __str__(self):
        label = "primary" if self.is_primary else "secondary"
        return f"{self.school_id} — {self.source} ({label})"


class OutreachEmail(models.Model):
    """Tracks outreach emails sent to schools."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SENT = "SENT", "Sent"
        FAILED = "FAILED", "Failed"
        BOUNCED = "BOUNCED", "Bounced"

    school = models.ForeignKey(
        "schools.School", on_delete=models.CASCADE, related_name="outreach_emails"
    )
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=300)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, default="")
    brevo_message_id = models.CharField(max_length=100, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.school_id} — {self.recipient_email} ({self.status})"
