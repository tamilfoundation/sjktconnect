from django.conf import settings
from django.db import models
from django.db.models import Q


class Broadcast(models.Model):
    """
    An email broadcast to a filtered set of subscribers.

    Created as DRAFT via the compose form, then sent (Sprint 2.3)
    via the Brevo transactional API.
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SENDING = "SENDING", "Sending"
        SENT = "SENT", "Sent"
        FAILED = "FAILED", "Failed"
        # Abandoned by an operator — never sent, never will be. Already
        # used in prod data (duplicate-blast repair 2026-05-02, stuck-
        # digest repair 2026-06-11) before being formalised here.
        # CANCELLED broadcasts neither advance the digest coverage anchor
        # nor suppress the next compose.
        CANCELLED = "CANCELLED", "Cancelled"

    class Kind(models.TextChoices):
        NEWS_DIGEST = "NEWS_DIGEST", "News Digest"
        URGENT_ALERT = "URGENT_ALERT", "Urgent Alert"
        MONTHLY_BLAST = "MONTHLY_BLAST", "Monthly Blast"
        PARLIAMENT_WATCH = "PARLIAMENT_WATCH", "Parliament Watch"
        OTHER = "OTHER", "Other"

    subject = models.CharField(max_length=300)
    html_content = models.TextField(blank=True, default="")
    text_content = models.TextField(blank=True, default="")
    audience_filter = models.JSONField(default=dict, blank=True)
    kind = models.CharField(
        max_length=20,
        choices=Kind.choices,
        default=Kind.OTHER,
        db_index=True,
    )
    coverage_start_date = models.DateField(null=True, blank=True)
    coverage_end_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.DRAFT
    )
    recipient_count = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    hero_image = models.BinaryField(
        null=True, blank=True, default=b"",
        help_text="Hero image PNG bytes for email header",
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # Audit 2026-07-01: DB-level guard against the 2026-05-02
            # duplicate-blast race (4 rows for one coverage window).
            # Application layer duplicate_guard.py still runs first; this
            # backstops it when two schedulers land inside the check
            # window. Non-null coverage dates only — historical rows
            # without coverage tracking (pre-Sprint-24) are left alone.
            models.UniqueConstraint(
                fields=["kind", "coverage_start_date", "coverage_end_date"],
                condition=Q(
                    status__in=["SENT", "SENDING"],
                    coverage_start_date__isnull=False,
                    coverage_end_date__isnull=False,
                ),
                name="unique_broadcast_per_kind_coverage",
            ),
        ]

    def __str__(self):
        return f"{self.subject} ({self.get_status_display()})"


class BroadcastRecipient(models.Model):
    """
    Per-recipient delivery tracking for a broadcast.

    The email field is denormalised so we retain a permanent audit trail
    even if the subscriber changes their email later.
    """

    class DeliveryStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SENT = "SENT", "Sent"
        DELIVERED = "DELIVERED", "Delivered"
        BOUNCED = "BOUNCED", "Bounced"
        SPAM = "SPAM", "Spam Complaint"
        FAILED = "FAILED", "Failed"

    class BounceType(models.TextChoices):
        HARD = "HARD", "Hard Bounce"
        SOFT = "SOFT", "Soft Bounce"

    broadcast = models.ForeignKey(
        Broadcast, on_delete=models.CASCADE, related_name="recipients"
    )
    subscriber = models.ForeignKey(
        "subscribers.Subscriber",
        on_delete=models.CASCADE,
        related_name="broadcast_recipients",
    )
    email = models.EmailField()  # Denormalised for audit trail
    status = models.CharField(
        max_length=10,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.PENDING,
    )
    brevo_message_id = models.CharField(max_length=100, blank=True, default="")
    sent_at = models.DateTimeField(null=True, blank=True)

    # Engagement tracking (populated by Brevo webhooks)
    delivered_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    open_count = models.PositiveIntegerField(default=0)
    clicked_at = models.DateTimeField(null=True, blank=True)
    click_count = models.PositiveIntegerField(default=0)
    bounce_type = models.CharField(
        max_length=4, choices=BounceType.choices, blank=True, default=""
    )

    class Meta:
        ordering = ["email"]
        constraints = [
            models.UniqueConstraint(
                fields=["broadcast", "subscriber"],
                name="unique_broadcast_subscriber",
            )
        ]

    def __str__(self):
        return f"{self.email} — {self.get_status_display()}"
