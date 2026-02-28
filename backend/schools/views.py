"""Schools app views — admin verification dashboard."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.views.generic import ListView

from accounts.models import SchoolContact
from schools.models import School


class VerificationDashboardView(LoginRequiredMixin, ListView):
    """Admin dashboard showing school data verification progress.

    Shows: overall progress bar, recently verified schools,
    unverified schools by state, contact management.
    """

    template_name = "schools/verification_dashboard.html"
    context_object_name = "schools"

    def get_queryset(self):
        return (
            School.objects.filter(is_active=True)
            .select_related("constituency")
            .order_by("-last_verified")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        active_schools = School.objects.filter(is_active=True)
        total = active_schools.count()
        verified = active_schools.exclude(last_verified=None).count()

        context["total_schools"] = total
        context["verified_count"] = verified
        context["unverified_count"] = total - verified
        context["progress_percent"] = round(verified / total * 100, 1) if total > 0 else 0

        # Recently verified (last 20)
        context["recently_verified"] = (
            active_schools.exclude(last_verified=None)
            .select_related("constituency")
            .order_by("-last_verified")[:20]
        )

        # Unverified by state
        context["unverified_by_state"] = (
            active_schools.filter(last_verified=None)
            .values("state")
            .annotate(count=Count("moe_code"))
            .order_by("-count")
        )

        # Verified contacts
        context["contacts"] = (
            SchoolContact.objects.filter(is_active=True)
            .select_related("school")
            .order_by("-verified_at")[:20]
        )

        return context
