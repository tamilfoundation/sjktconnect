from django.db import models


class HansardSitting(models.Model):
    """A single day's parliamentary Hansard session."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    sitting_date = models.DateField(unique=True, db_index=True)
    session = models.CharField(max_length=50, blank=True, default="")
    meeting_number = models.CharField(max_length=50, blank=True, default="")
    pdf_url = models.URLField(max_length=500)
    pdf_filename = models.CharField(max_length=200)
    total_pages = models.IntegerField(null=True, blank=True)
    mention_count = models.IntegerField(default=0)
    processed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sitting_date"]

    def __str__(self):
        return f"{self.sitting_date} ({self.get_status_display()})"


class HansardMention(models.Model):
    """A single mention of Tamil school keywords found in a Hansard sitting."""

    sitting = models.ForeignKey(
        HansardSitting, on_delete=models.CASCADE, related_name="mentions"
    )
    page_number = models.IntegerField(null=True, blank=True)
    verbatim_quote = models.TextField()
    context_before = models.TextField(blank=True, default="")
    context_after = models.TextField(blank=True, default="")
    keyword_matched = models.CharField(max_length=100, blank=True, default="")

    # AI fields (populated in Sprint 0.4)
    mp_name = models.CharField(max_length=100, blank=True, default="")
    mp_constituency = models.CharField(max_length=100, blank=True, default="")
    mp_party = models.CharField(max_length=100, blank=True, default="")
    mention_type = models.CharField(max_length=20, blank=True, default="")
    significance = models.IntegerField(null=True, blank=True)
    sentiment = models.CharField(max_length=20, blank=True, default="")
    change_indicator = models.CharField(max_length=20, blank=True, default="")
    ai_summary = models.TextField(blank=True, default="")
    ai_raw_response = models.JSONField(default=dict, blank=True)

    # Review fields (Sprint 0.5)
    review_status = models.CharField(max_length=20, blank=True, default="PENDING")
    reviewed_by = models.CharField(max_length=100, blank=True, default="")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sitting", "page_number"]

    def __str__(self):
        keyword = self.keyword_matched or "unknown"
        return f"Mention: '{keyword}' on p.{self.page_number}"
