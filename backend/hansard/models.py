from django.db import models

from schools.models import School


class HansardSitting(models.Model):
    """A single day's parliamentary Hansard session."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    sitting_date = models.DateField(unique=True, db_index=True)
    meeting = models.ForeignKey(
        "parliament.ParliamentaryMeeting",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="sittings",
    )
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
    speaker_verified = models.BooleanField(default=True)
    eval_warnings = models.JSONField(default=list, blank=True)
    eval_confidence = models.FloatField(default=1.0)

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


class SchoolAlias(models.Model):
    """An alias for a School used in Hansard matching.

    Each school can have multiple aliases (official name, short name,
    Malay translation, common abbreviation, Hansard-specific variant).
    The normalised form is used for exact matching; the raw alias is
    preserved for display.
    """

    class AliasType(models.TextChoices):
        OFFICIAL = "OFFICIAL", "Official MOE name"
        SHORT = "SHORT", "Short name"
        MALAY = "MALAY", "Malay translation"
        COMMON = "COMMON", "Common variant"
        HANSARD = "HANSARD", "Found in Hansard"

    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name="aliases"
    )
    alias = models.CharField(max_length=200, db_index=True)
    alias_normalized = models.CharField(max_length=200, db_index=True)
    alias_type = models.CharField(
        max_length=20, choices=AliasType.choices, default=AliasType.COMMON
    )

    class Meta:
        unique_together = [("school", "alias_normalized")]
        verbose_name_plural = "school aliases"

    def __str__(self):
        return f"{self.alias} → {self.school.short_name}"


class MentionedSchool(models.Model):
    """Bridge table linking a HansardMention to a matched School.

    Created by the matcher pipeline (Sprint 0.3). A single mention
    can reference multiple schools; a single school can appear in
    multiple mentions.
    """

    class MatchMethod(models.TextChoices):
        EXACT = "EXACT", "Exact alias match"
        TRIGRAM = "TRIGRAM", "Trigram similarity"
        MANUAL = "MANUAL", "Manual review"

    mention = models.ForeignKey(
        HansardMention, on_delete=models.CASCADE, related_name="matched_schools"
    )
    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name="hansard_matches"
    )
    confidence_score = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="0-100 confidence score",
    )
    matched_by = models.CharField(
        max_length=20, choices=MatchMethod.choices, default=MatchMethod.EXACT
    )
    matched_text = models.CharField(
        max_length=200, blank=True, default="",
        help_text="The text fragment that was matched",
    )
    needs_review = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("mention", "school")]

    def __str__(self):
        return f"{self.school.short_name} ({self.get_matched_by_display()}, {self.confidence_score}%)"
