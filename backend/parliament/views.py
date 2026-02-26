"""Parliament app views — admin review queue and public parliament watch."""

import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, ListView

from hansard.models import HansardMention, HansardSitting
from parliament.forms import MentionReviewForm
from parliament.models import SittingBrief
from parliament.services.brief_generator import generate_brief

logger = logging.getLogger(__name__)


# --- Admin views (login required) ---


class ReviewQueueView(LoginRequiredMixin, ListView):
    """List sittings with pending mentions, grouped by date."""

    template_name = "parliament/queue.html"
    context_object_name = "sittings"

    def get_queryset(self):
        return (
            HansardSitting.objects
            .filter(mentions__isnull=False)
            .annotate(
                pending_count=Count(
                    "mentions", filter=Q(mentions__review_status="PENDING")
                ),
                approved_count=Count(
                    "mentions", filter=Q(mentions__review_status="APPROVED")
                ),
                rejected_count=Count(
                    "mentions", filter=Q(mentions__review_status="REJECTED")
                ),
                total_mention_count=Count("mentions"),
            )
            .filter(total_mention_count__gt=0)
            .order_by("-sitting_date")
        )


class MentionDetailView(LoginRequiredMixin, DetailView):
    """Split-screen review: left = verbatim quote, right = editable AI analysis."""

    template_name = "parliament/detail.html"
    model = HansardMention
    context_object_name = "mention"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form"] = MentionReviewForm(instance=self.object)
        # Sibling mentions in the same sitting for navigation
        ctx["siblings"] = (
            self.object.sitting.mentions
            .order_by("page_number")
            .values_list("pk", "page_number", "review_status")
        )
        return ctx


class ApproveMentionView(LoginRequiredMixin, View):
    """Approve a mention (optionally with edits)."""

    def post(self, request, pk):
        mention = get_object_or_404(HansardMention, pk=pk)
        form = MentionReviewForm(request.POST, instance=mention)

        if form.is_valid():
            mention = form.save(commit=False)
            mention.review_status = "APPROVED"
            mention.reviewed_by = request.user.get_username()
            mention.reviewed_at = timezone.now()
            mention.save()
            logger.info("Mention %s approved by %s", pk, request.user)

        return redirect("parliament:sitting-review", sitting_pk=mention.sitting_id)


class RejectMentionView(LoginRequiredMixin, View):
    """Reject a mention."""

    def post(self, request, pk):
        mention = get_object_or_404(HansardMention, pk=pk)
        mention.review_status = "REJECTED"
        mention.reviewed_by = request.user.get_username()
        mention.reviewed_at = timezone.now()
        mention.review_notes = request.POST.get("review_notes", "")
        mention.save(update_fields=[
            "review_status", "reviewed_by", "reviewed_at",
            "review_notes", "updated_at",
        ])
        logger.info("Mention %s rejected by %s", pk, request.user)
        return redirect("parliament:sitting-review", sitting_pk=mention.sitting_id)


class SittingReviewView(LoginRequiredMixin, ListView):
    """List all mentions for a single sitting for review."""

    template_name = "parliament/sitting_review.html"
    context_object_name = "mentions"

    def get_queryset(self):
        self.sitting = get_object_or_404(
            HansardSitting, pk=self.kwargs["sitting_pk"]
        )
        return self.sitting.mentions.order_by("page_number")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["sitting"] = self.sitting
        return ctx


class PublishBriefView(LoginRequiredMixin, View):
    """Generate and publish a SittingBrief."""

    def post(self, request, sitting_pk):
        sitting = get_object_or_404(HansardSitting, pk=sitting_pk)
        brief = generate_brief(sitting)
        if brief:
            brief.is_published = True
            brief.published_at = timezone.now()
            brief.save(update_fields=["is_published", "published_at", "updated_at"])
            logger.info(
                "Brief for %s published by %s",
                sitting.sitting_date, request.user,
            )
        return redirect("parliament:sitting-review", sitting_pk=sitting.pk)


# --- Public views ---


class ParliamentWatchView(ListView):
    """Published briefs listed as cards."""

    template_name = "parliament/watch.html"
    context_object_name = "briefs"

    def get_queryset(self):
        return SittingBrief.objects.filter(
            is_published=True,
        ).select_related("sitting")


class BriefDetailView(DetailView):
    """Single published brief detail page."""

    template_name = "parliament/brief.html"
    context_object_name = "brief"

    def get_object(self):
        return get_object_or_404(
            SittingBrief,
            sitting__sitting_date=self.kwargs["sitting_date"],
            is_published=True,
        )
