from django.db import models

from hansard.models import HansardSitting
from schools.models import Constituency


class MPScorecard(models.Model):
    """Aggregated engagement scorecard for a Member of Parliament.

    Tracks how often an MP mentions Tamil schools in Hansard,
    broken down by mention quality (substantive vs throwaway).
    Recalculated by the update_scorecards management command.
    """

    mp_name = models.CharField(max_length=100)
    constituency = models.ForeignKey(
        Constituency, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="scorecards",
    )
    party = models.CharField(max_length=100, blank=True, default="")
    coalition = models.CharField(max_length=50, blank=True, default="")
    total_mentions = models.IntegerField(default=0)
    substantive_mentions = models.IntegerField(
        default=0,
        help_text="Mentions with significance >= 3",
    )
    questions_asked = models.IntegerField(
        default=0,
        help_text="Mentions with type QUESTION",
    )
    commitments_made = models.IntegerField(
        default=0,
        help_text="Mentions with type COMMITMENT or sentiment PROMISING",
    )
    last_mention_date = models.DateField(null=True, blank=True)
    school_count = models.IntegerField(
        default=0,
        help_text="Number of SJK(T) schools in this constituency",
    )
    total_enrolment = models.IntegerField(
        default=0,
        help_text="Total enrolment across constituency schools",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("mp_name", "constituency")]
        ordering = ["-total_mentions"]

    def __str__(self):
        return f"{self.mp_name} ({self.constituency or 'Unknown'})"


class SittingBrief(models.Model):
    """AI-generated brief summarising Tamil school mentions in a sitting.

    Created by brief_generator.py after mentions are analysed and approved.
    Published at /parliament-watch/<sitting_date>/ (Sprint 0.5).
    """

    sitting = models.OneToOneField(
        HansardSitting, on_delete=models.CASCADE, related_name="brief",
    )
    title = models.CharField(max_length=300)
    summary_html = models.TextField(
        help_text="Rendered HTML from markdown summary",
    )
    social_post_text = models.TextField(
        blank=True, default="",
        help_text="Social media post text, max 280 chars",
    )
    email_draft_html = models.TextField(
        blank=True, default="",
        help_text="Email newsletter draft",
    )
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-sitting__sitting_date"]

    def __str__(self):
        status = "Published" if self.is_published else "Draft"
        return f"Brief: {self.sitting.sitting_date} ({status})"
