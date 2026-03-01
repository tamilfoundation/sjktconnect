"""Newswatch views — admin review queue for AI-analysed news articles."""

import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View
from django.views.generic import ListView, DetailView

from newswatch.models import NewsArticle

logger = logging.getLogger(__name__)


class NewsQueueView(LoginRequiredMixin, ListView):
    """List analysed articles pending review, urgent first."""

    template_name = "newswatch/queue.html"
    context_object_name = "articles"
    paginate_by = 25

    def get_queryset(self):
        qs = NewsArticle.objects.filter(status=NewsArticle.ANALYSED)

        # Filter by review status if specified
        review_filter = self.request.GET.get("review")
        if review_filter in ("PENDING", "APPROVED", "REJECTED"):
            qs = qs.filter(review_status=review_filter)

        # Filter by urgency if specified
        urgent_filter = self.request.GET.get("urgent")
        if urgent_filter == "1":
            qs = qs.filter(is_urgent=True)

        return qs.order_by("-is_urgent", "-relevance_score", "-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        analysed = NewsArticle.objects.filter(status=NewsArticle.ANALYSED)
        ctx["pending_count"] = analysed.filter(review_status=NewsArticle.PENDING).count()
        ctx["approved_count"] = analysed.filter(review_status=NewsArticle.APPROVED).count()
        ctx["rejected_count"] = analysed.filter(review_status=NewsArticle.REJECTED).count()
        ctx["urgent_count"] = analysed.filter(
            is_urgent=True, review_status=NewsArticle.PENDING,
        ).count()
        ctx["current_review"] = self.request.GET.get("review", "")
        ctx["current_urgent"] = self.request.GET.get("urgent", "")
        return ctx


class NewsArticleDetailView(LoginRequiredMixin, DetailView):
    """Detail view for reviewing a single news article."""

    template_name = "newswatch/detail.html"
    model = NewsArticle
    context_object_name = "article"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Sibling articles for navigation (same batch, nearby by date)
        ctx["siblings"] = (
            NewsArticle.objects.filter(status=NewsArticle.ANALYSED)
            .order_by("-is_urgent", "-relevance_score", "-created_at")
            .values_list("pk", "title", "review_status", "is_urgent")[:20]
        )
        return ctx


class ApproveArticleView(LoginRequiredMixin, View):
    """Approve an analysed article."""

    def post(self, request, pk):
        article = get_object_or_404(NewsArticle, pk=pk)
        article.review_status = NewsArticle.APPROVED
        article.reviewed_by = request.user
        article.reviewed_at = timezone.now()
        article.save(update_fields=[
            "review_status", "reviewed_by", "reviewed_at", "updated_at",
        ])
        logger.info("Article %s approved by %s", pk, request.user)
        return redirect("newswatch:news-queue")


class RejectArticleView(LoginRequiredMixin, View):
    """Reject an analysed article (not relevant / false positive)."""

    def post(self, request, pk):
        article = get_object_or_404(NewsArticle, pk=pk)
        article.review_status = NewsArticle.REJECTED
        article.reviewed_by = request.user
        article.reviewed_at = timezone.now()
        article.save(update_fields=[
            "review_status", "reviewed_by", "reviewed_at", "updated_at",
        ])
        logger.info("Article %s rejected by %s", pk, request.user)
        return redirect("newswatch:news-queue")


class ToggleUrgentView(LoginRequiredMixin, View):
    """Toggle urgent flag on an article."""

    def post(self, request, pk):
        article = get_object_or_404(NewsArticle, pk=pk)
        article.is_urgent = not article.is_urgent
        if not article.is_urgent:
            article.urgent_reason = ""
        article.save(update_fields=["is_urgent", "urgent_reason", "updated_at"])
        logger.info(
            "Article %s urgent=%s by %s", pk, article.is_urgent, request.user,
        )
        return redirect("newswatch:news-detail", pk=pk)
