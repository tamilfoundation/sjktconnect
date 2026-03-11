import uuid

from django.db import models


class Subscriber(models.Model):
    """
    A person who subscribes to SJK(T) Connect communications.

    Separate from SchoolContact — subscribers include community leaders,
    journalists, MPs' offices, and anyone interested in Tamil school
    intelligence. Not necessarily tied to a specific school.
    """

    email = models.EmailField(unique=True, db_index=True)
    name = models.CharField(max_length=200, blank=True, default="")
    organisation = models.CharField(max_length=300, blank=True, default="")
    is_active = models.BooleanField(
        default=True,
        help_text="False when unsubscribed.",
    )
    source = models.CharField(
        max_length=30, blank=True, default="",
        help_text="How they were added: WEBSITE, BULK_IMPORT, etc.",
    )
    source_tag = models.CharField(
        max_length=50, blank=True, default="",
        help_text="Sub-category: Thulivellam, Member, etc.",
    )
    donor_status = models.CharField(
        max_length=30, blank=True, default="",
        help_text="Original membership status from import.",
    )
    unsubscribe_token = models.UUIDField(
        default=uuid.uuid4, unique=True, db_index=True
    )
    subscribed_at = models.DateTimeField(auto_now_add=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-subscribed_at"]

    def __str__(self):
        status = "active" if self.is_active else "unsubscribed"
        return f"{self.email} ({status})"


class SubscriptionPreference(models.Model):
    """
    Per-subscriber toggle for each communication category.

    Categories:
    - PARLIAMENT_WATCH: Hansard analysis briefs
    - NEWS_WATCH: News monitoring alerts
    - MONTHLY_BLAST: Monthly Intelligence Blast digest
    """

    PARLIAMENT_WATCH = "PARLIAMENT_WATCH"
    NEWS_WATCH = "NEWS_WATCH"
    MONTHLY_BLAST = "MONTHLY_BLAST"

    CATEGORY_CHOICES = [
        (PARLIAMENT_WATCH, "Parliament Watch"),
        (NEWS_WATCH, "News Watch"),
        (MONTHLY_BLAST, "Monthly Intelligence Blast"),
    ]

    subscriber = models.ForeignKey(
        Subscriber, on_delete=models.CASCADE, related_name="preferences"
    )
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    is_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("subscriber", "category")]
        ordering = ["category"]

    def __str__(self):
        status = "on" if self.is_enabled else "off"
        return f"{self.subscriber.email} — {self.get_category_display()} ({status})"
