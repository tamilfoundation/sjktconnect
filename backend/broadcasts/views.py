"""Broadcast views — compose, preview, send, and list broadcasts."""

import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from broadcasts.models import Broadcast, BroadcastRecipient
from broadcasts.services.audience import get_filtered_subscribers
from broadcasts.services.sender import send_broadcast, send_test
from schools.models import School

logger = logging.getLogger(__name__)


class SuperuserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Gate a CBV behind `is_authenticated AND is_superuser`.

    Until TD-20 (audit 2026-06-26), broadcast views relied on the
    architectural invariant "Google OAuth doesn't create a Django User
    row" for role gating — i.e. only `manage.py createsuperuser` users
    could pass `LoginRequiredMixin`. That invariant was undocumented
    and untested; if django-allauth were ever wired in, every broadcast
    endpoint would silently become accessible to any signed-in user
    (including `POST /broadcast/send/<pk>/` which fires a blast to all
    ~519 subscribers, and `POST /broadcast/send-test/<pk>/` which is a
    Brevo-quota-bypassing spam relay).

    Defense-in-depth: explicit `is_superuser` check. Anonymous users
    redirect to login (LoginRequiredMixin default); authenticated
    non-superusers get 403 (PermissionDenied).
    """

    def test_func(self):
        return self.request.user.is_superuser

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            # Authenticated but failed test_func — raise 403.
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied()
        # Anonymous — fall through to LoginRequiredMixin's redirect-to-login.
        return super().handle_no_permission()


class BroadcastListView(SuperuserRequiredMixin, ListView):
    """List all broadcasts with status, subject, kind, and dates.

    Sprint 25: supports `?kind=URGENT_ALERT` etc. so admins can quickly
    surface DRAFT urgent alerts or Parliament Watch broadcasts amid the
    monthly blast / news digest history.
    """

    model = Broadcast
    template_name = "broadcasts/broadcast_list.html"
    context_object_name = "broadcasts"
    paginate_by = 50

    def get_queryset(self):
        qs = super().get_queryset()
        kind = self.request.GET.get("kind", "").strip()
        if kind and kind in Broadcast.Kind.values:
            qs = qs.filter(kind=kind)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["kind_choices"] = Broadcast.Kind.choices
        context["selected_kind"] = self.request.GET.get("kind", "")
        return context


class BroadcastComposeView(SuperuserRequiredMixin, TemplateView):
    """Compose a new broadcast with subject, content, and audience filters."""

    template_name = "broadcasts/broadcast_compose.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["states"] = (
            School.objects.values_list("state", flat=True)
            .distinct()
            .order_by("state")
        )
        context["ppds"] = (
            School.objects.exclude(ppd="")
            .values_list("ppd", flat=True)
            .distinct()
            .order_by("ppd")
        )
        return context

    def post(self, request, *args, **kwargs):
        subject = request.POST.get("subject", "").strip()
        html_content = request.POST.get("html_content", "").strip()
        text_content = request.POST.get("text_content", "").strip()

        # C2: Validate subject is not empty
        if not subject:
            context = self.get_context_data()
            context["error"] = "Subject is required."
            context["form_data"] = request.POST
            return self.render_to_response(context)

        # Build audience filter from form fields
        audience_filter = {}
        for field in ["state", "constituency", "ppd"]:
            value = request.POST.get(field, "").strip()
            if value:
                audience_filter[field] = value

        # C3: Safely parse enrolment values
        min_enrolment = request.POST.get("min_enrolment", "").strip()
        if min_enrolment:
            try:
                audience_filter["min_enrolment"] = int(min_enrolment)
            except ValueError:
                pass  # Ignore invalid enrolment input

        max_enrolment = request.POST.get("max_enrolment", "").strip()
        if max_enrolment:
            try:
                audience_filter["max_enrolment"] = int(max_enrolment)
            except ValueError:
                pass  # Ignore invalid enrolment input

        if request.POST.get("skm"):
            audience_filter["skm"] = True

        category = request.POST.get("category", "").strip()
        if category:
            audience_filter["category"] = category

        # Calculate recipient count
        recipients = get_filtered_subscribers(audience_filter)
        recipient_count = recipients.count()

        broadcast = Broadcast.objects.create(
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            audience_filter=audience_filter,
            recipient_count=recipient_count,
            created_by=request.user,
        )

        return redirect("broadcasts:broadcast-preview", pk=broadcast.pk)


class BroadcastPreviewView(SuperuserRequiredMixin, TemplateView):
    """Preview a broadcast before sending."""

    template_name = "broadcasts/broadcast_preview.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        broadcast = get_object_or_404(Broadcast, pk=kwargs["pk"])
        context["broadcast"] = broadcast

        # Recalculate recipient count from current filter
        recipients = get_filtered_subscribers(broadcast.audience_filter)
        context["recipient_count"] = recipients.count()

        # Build human-readable filter summary
        af = broadcast.audience_filter
        summary_parts = []
        if af.get("state"):
            summary_parts.append(f"State: {af['state']}")
        if af.get("constituency"):
            summary_parts.append(f"Constituency: {af['constituency']}")
        if af.get("ppd"):
            summary_parts.append(f"PPD: {af['ppd']}")
        if af.get("min_enrolment"):
            summary_parts.append(f"Min enrolment: {af['min_enrolment']}")
        if af.get("max_enrolment"):
            summary_parts.append(f"Max enrolment: {af['max_enrolment']}")
        if af.get("skm"):
            summary_parts.append("SKM eligible only")
        if af.get("category"):
            summary_parts.append(f"Category: {af['category']}")
        context["filter_summary"] = summary_parts or ["All active subscribers"]

        return context


class BroadcastSendView(SuperuserRequiredMixin, View):
    """POST-only view to trigger sending a DRAFT broadcast."""

    def post(self, request, pk):
        broadcast = get_object_or_404(Broadcast, pk=pk)

        if broadcast.status != Broadcast.Status.DRAFT:
            messages.error(
                request,
                "This broadcast has already been sent or is currently sending.",
            )
            return redirect("broadcasts:broadcast-detail", pk=pk)

        try:
            send_broadcast(broadcast.pk)
            messages.success(request, "Broadcast sent successfully.")
        except Exception as exc:
            logger.exception("Failed to send broadcast %s: %s", pk, exc)
            messages.error(
                request, "Failed to send broadcast. Please try again."
            )

        return redirect("broadcasts:broadcast-detail", pk=pk)


class BroadcastSendTestView(SuperuserRequiredMixin, View):
    """POST-only view to send a DRAFT broadcast to a list of test addresses.

    Sprint 25: lets the admin verify a Parliament Watch / Urgent Alert /
    News Digest draft on their own inbox before releasing it to ~519
    subscribers. Does NOT change `broadcast.status`, does NOT create
    `BroadcastRecipient` rows. Always returns to the preview page with a
    flash message.
    """

    def post(self, request, pk):
        broadcast = get_object_or_404(Broadcast, pk=pk)
        raw = request.POST.get("recipients", "").strip()
        recipients = [
            email.strip() for email in raw.split(",") if email.strip()
        ]
        if not recipients:
            messages.error(
                request,
                "Enter at least one test recipient email address.",
            )
            return redirect("broadcasts:broadcast-preview", pk=pk)
        if len(recipients) > 5:
            messages.error(
                request,
                "Test sends are capped at 5 recipients. Send the broadcast "
                "for real once you're satisfied with a smaller test.",
            )
            return redirect("broadcasts:broadcast-preview", pk=pk)

        try:
            sent, failed = send_test(broadcast.pk, recipients)
        except Exception as exc:
            logger.exception("Test send failed for broadcast %s: %s", pk, exc)
            messages.error(
                request, "Test send failed. Check server logs for details."
            )
            return redirect("broadcasts:broadcast-preview", pk=pk)

        if failed:
            messages.warning(
                request,
                f"Test sent: {sent} succeeded, {failed} failed. "
                "Broadcast status unchanged.",
            )
        else:
            messages.success(
                request,
                f"Test sent to {sent} recipient(s). Broadcast status unchanged.",
            )
        return redirect("broadcasts:broadcast-preview", pk=pk)


class BroadcastDetailView(SuperuserRequiredMixin, DetailView):
    """Show broadcast details with per-recipient delivery status."""

    model = Broadcast
    template_name = "broadcasts/broadcast_detail.html"
    context_object_name = "broadcast"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["recipients"] = (
            self.object.recipients.select_related("subscriber")
            .order_by("email")
        )
        return context
