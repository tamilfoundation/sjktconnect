from django.db import models

from hansard.models import HansardSitting
from schools.models import Constituency


class ParliamentaryMeeting(models.Model):
    """A parliamentary meeting period (not a single sitting).

    Represents a meeting within a parliamentary term, e.g. "First Meeting
    of the Fourth Term 2025". Contains multiple sittings and an AI-generated
    executive-grade policy report synthesising all sitting summaries.
    """

    name = models.CharField(
        max_length=200,
        help_text="e.g. First Meeting of the Fourth Term 2025",
    )
    short_name = models.CharField(
        max_length=50,
        help_text="e.g. 1st Meeting 2025",
    )
    term = models.PositiveIntegerField(
        help_text="Parliamentary term (4 = 2025, 5 = 2026)",
    )
    session = models.PositiveIntegerField(
        help_text="Meeting number within term (1, 2, 3, or 0 for Special)",
    )
    year = models.PositiveIntegerField()
    start_date = models.DateField(help_text="First sitting date")
    end_date = models.DateField(help_text="Last sitting date")
    report_html = models.TextField(
        blank=True, default="",
        help_text="Gemini-generated 7-point meeting report (HTML)",
    )
    executive_summary = models.TextField(
        blank=True, default="",
        help_text="First 2-3 paragraphs for preview/cards",
    )
    social_post_text = models.TextField(
        blank=True, default="",
        help_text="280-char social summary",
    )
    illustration = models.BinaryField(
        blank=True, default=b"",
        help_text="Gemini-generated editorial cartoon (PNG bytes)",
    )
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("term", "session", "year")]
        ordering = ["-start_date"]

    def __str__(self):
        status = "Published" if self.is_published else "Draft"
        return f"{self.short_name} ({status})"


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


class MP(models.Model):
    """Member of Parliament profile with contact details."""
    constituency = models.OneToOneField(
        Constituency, on_delete=models.CASCADE, related_name="mp",
    )
    name = models.CharField(max_length=200)
    photo_url = models.URLField(max_length=500, blank=True, default="")
    party = models.CharField(max_length=100, blank=True, default="")
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=50, null=True, blank=True)
    fax = models.CharField(max_length=50, null=True, blank=True)
    facebook_url = models.URLField(max_length=500, null=True, blank=True)
    twitter_url = models.URLField(max_length=500, null=True, blank=True)
    instagram_url = models.URLField(max_length=500, null=True, blank=True)
    website_url = models.URLField(max_length=500, null=True, blank=True)
    service_centre_address = models.TextField(null=True, blank=True)
    parlimen_profile_id = models.CharField(max_length=20, blank=True, default="")
    mymp_slug = models.CharField(max_length=200, blank=True, default="")
    last_scraped = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "MP"
        verbose_name_plural = "MPs"

    def __str__(self):
        return f"{self.name} ({self.constituency.code})"

    @property
    def parlimen_profile_url(self):
        if self.parlimen_profile_id:
            return f"https://www.parlimen.gov.my/profile-ahli.html?uweb=dr&id={self.parlimen_profile_id}"
        return None

    @property
    def mymp_profile_url(self):
        if self.mymp_slug:
            return f"https://mymp.org.my/p/{self.mymp_slug}"
        return None
