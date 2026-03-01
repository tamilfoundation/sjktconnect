from django.conf import settings
from django.db import models


class NewsArticle(models.Model):
    """
    A news article about Tamil schools discovered via Google Alerts RSS.

    Lifecycle: NEW → EXTRACTED (body text fetched) or FAILED (extraction error)
               → ANALYSED (AI analysis complete).
    """

    NEW = "NEW"
    EXTRACTED = "EXTRACTED"
    FAILED = "FAILED"
    ANALYSED = "ANALYSED"

    STATUS_CHOICES = [
        (NEW, "New"),
        (EXTRACTED, "Extracted"),
        (FAILED, "Failed"),
        (ANALYSED, "Analysed"),
    ]

    # Sentiment choices for AI analysis
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    MIXED = "MIXED"

    SENTIMENT_CHOICES = [
        (POSITIVE, "Positive"),
        (NEGATIVE, "Negative"),
        (NEUTRAL, "Neutral"),
        (MIXED, "Mixed"),
    ]

    # Review status choices
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

    REVIEW_STATUS_CHOICES = [
        (PENDING, "Pending"),
        (APPROVED, "Approved"),
        (REJECTED, "Rejected"),
    ]

    # --- Core fields (Sprint 2.5) ---
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

    # --- AI analysis fields (Sprint 2.6) ---
    relevance_score = models.IntegerField(
        null=True, blank=True,
        help_text="AI relevance to Tamil schools (1-5, 5 = highly relevant)",
    )
    sentiment = models.CharField(
        max_length=10, choices=SENTIMENT_CHOICES,
        blank=True, default="",
        help_text="AI-assessed sentiment towards Tamil schools",
    )
    ai_summary = models.TextField(
        blank=True, default="",
        help_text="AI-generated 2-3 sentence summary",
    )
    mentioned_schools = models.JSONField(
        default=list, blank=True,
        help_text="List of school names/codes mentioned (AI-extracted)",
    )
    ai_raw_response = models.JSONField(
        default=dict, blank=True,
        help_text="Raw Gemini response for audit",
    )
    is_urgent = models.BooleanField(
        default=False, db_index=True,
        help_text="Flagged for rapid response (closure threat, crisis, etc.)",
    )
    urgent_reason = models.CharField(
        max_length=500, blank=True, default="",
        help_text="AI explanation of why this is urgent",
    )

    # --- Review fields (Sprint 2.6) ---
    review_status = models.CharField(
        max_length=10, choices=REVIEW_STATUS_CHOICES,
        default=PENDING, db_index=True,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_articles",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # --- Timestamps ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title[:80]} ({self.status})"
