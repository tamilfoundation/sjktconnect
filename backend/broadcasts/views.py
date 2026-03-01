"""Broadcast views — compose, preview, and list broadcasts."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, TemplateView

from broadcasts.models import Broadcast
from broadcasts.services.audience import get_filtered_subscribers
from schools.models import School


# States for the dropdown — derived from School data
MALAYSIAN_STATES = [
    "JOHOR",
    "KEDAH",
    "KELANTAN",
    "MELAKA",
    "NEGERI SEMBILAN",
    "PAHANG",
    "PERAK",
    "PERLIS",
    "PULAU PINANG",
    "SELANGOR",
    "WILAYAH PERSEKUTUAN KUALA LUMPUR",
]


class BroadcastListView(LoginRequiredMixin, ListView):
    """List all broadcasts with status, subject, and dates."""

    model = Broadcast
    template_name = "broadcasts/broadcast_list.html"
    context_object_name = "broadcasts"


class BroadcastComposeView(LoginRequiredMixin, TemplateView):
    """Compose a new broadcast with subject, content, and audience filters."""

    template_name = "broadcasts/broadcast_compose.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["states"] = MALAYSIAN_STATES
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

        # Build audience filter from form fields
        audience_filter = {}
        for field in ["state", "constituency", "ppd"]:
            value = request.POST.get(field, "").strip()
            if value:
                audience_filter[field] = value

        min_enrolment = request.POST.get("min_enrolment", "").strip()
        if min_enrolment:
            audience_filter["min_enrolment"] = int(min_enrolment)

        max_enrolment = request.POST.get("max_enrolment", "").strip()
        if max_enrolment:
            audience_filter["max_enrolment"] = int(max_enrolment)

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
        )

        return redirect("broadcasts:broadcast-preview", pk=broadcast.pk)


class BroadcastPreviewView(LoginRequiredMixin, TemplateView):
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
