from django.db import models


class NewsArticle(models.Model):
    """
    A news article about Tamil schools discovered via Google Alerts RSS.

    Lifecycle: NEW → EXTRACTED (body text fetched) or FAILED (extraction error).
    AI analysis happens in Sprint 2.6.
    """

    NEW = "NEW"
    EXTRACTED = "EXTRACTED"
    FAILED = "FAILED"

    STATUS_CHOICES = [
        (NEW, "New"),
        (EXTRACTED, "Extracted"),
        (FAILED, "Failed"),
    ]

    url = models.URLField(max_length=2000, unique=True, db_index=True)
    title = models.CharField(max_length=500)
    source_name = models.CharField(
        max_length=200, blank=True, default="",
        help_text="Publication name (e.g. The Star, Malaysiakini)",
    )
    alert_title = models.CharField(
        max_length=500, blank=True, default="",
        help_text="Google Alerts feed title that surfaced this article",
    )
    published_date = models.DateTimeField(
        null=True, blank=True,
        help_text="Article publication date from RSS or extraction",
    )
    body_text = models.TextField(
        blank=True, default="",
        help_text="Extracted article body text (plain text, no HTML)",
    )
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default=NEW, db_index=True,
    )
    extraction_error = models.TextField(
        blank=True, default="",
        help_text="Error message if extraction failed",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title[:80]} ({self.status})"
