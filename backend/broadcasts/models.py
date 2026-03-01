from django.conf import settings
from django.db import models


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

    subject = models.CharField(max_length=300)
    html_content = models.TextField(blank=True, default="")
    text_content = models.TextField(blank=True, default="")
    audience_filter = models.JSONField(default=dict, blank=True)
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

    class Meta:
        ordering = ["-created_at"]

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
        FAILED = "FAILED", "Failed"

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
