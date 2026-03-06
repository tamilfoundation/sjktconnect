from django.db import models


class InboundEmail(models.Model):
    """
    An email received in reply to an SJK(T) Connect broadcast.

    Stores the raw email content and metadata for AI classification
    and response tracking.
    """

    CLASSIFICATION_CHOICES = [
        ("UNCLASSIFIED", "Unclassified"),
        ("CORRECTION", "Correction"),
        ("TIP", "Tip"),
        ("COMPLAINT", "Complaint"),
        ("PRAISE", "Praise"),
        ("QUESTION", "Question"),
        ("UNSUBSCRIBE", "Unsubscribe"),
        ("IRRELEVANT", "Irrelevant"),
    ]

    RESPONSE_STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("AUTO_RESPONDED", "Auto-responded"),
        ("ESCALATED", "Escalated"),
        ("RESOLVED", "Resolved"),
    ]

    gmail_message_id = models.CharField(max_length=200, unique=True)
    gmail_thread_id = models.CharField(max_length=200, blank=True, default="")
    from_email = models.EmailField()
    from_name = models.CharField(max_length=200, blank=True, default="")
    subject = models.CharField(max_length=500)
    body_text = models.TextField()
    source_broadcast_type = models.CharField(max_length=30, blank=True, default="")
    classification = models.CharField(
        max_length=20,
        choices=CLASSIFICATION_CHOICES,
        default="UNCLASSIFIED",
    )
    classification_reasoning = models.TextField(blank=True, default="")
    response_status = models.CharField(
        max_length=20,
        choices=RESPONSE_STATUS_CHOICES,
        default="PENDING",
    )
    auto_response_text = models.TextField(blank=True, default="")
    escalated = models.BooleanField(default=False)
    received_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-received_at"]

    def __str__(self):
        return f"{self.from_email} — {self.subject[:60]}"
