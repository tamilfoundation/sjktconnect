from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import path

from broadcasts.models import Broadcast
from broadcasts.views import (
    BroadcastComposeView,
    BroadcastDetailView,
    BroadcastListView,
    BroadcastPreviewView,
    BroadcastSendTestView,
    BroadcastSendView,
)


def broadcast_hero_image_view(request, pk):
    """Serve the broadcast hero image as a PNG.

    Deliberately unauthenticated: hero images are embedded in marketing
    emails sent to ~519 subscribers, so the content is intentionally
    public. Sequential `pk` enumeration leaks the broadcast count but
    not subjects / recipients (those live in `BroadcastDetailView`
    which IS auth-gated). If hero images ever need access control,
    migrate to Supabase Storage (consistent with community/school
    images post-Sprint-13) and serve via signed URLs. — TD-25, 2026-06-26.
    """
    broadcast = get_object_or_404(Broadcast, pk=pk)
    if not broadcast.hero_image:
        return HttpResponse(status=404)
    return HttpResponse(
        bytes(broadcast.hero_image),
        content_type="image/png",
    )


app_name = "broadcasts"

urlpatterns = [
    path("broadcast/", BroadcastListView.as_view(), name="broadcast-list"),
    path(
        "broadcast/compose/",
        BroadcastComposeView.as_view(),
        name="broadcast-compose",
    ),
    path(
        "broadcast/preview/<int:pk>/",
        BroadcastPreviewView.as_view(),
        name="broadcast-preview",
    ),
    path(
        "broadcast/send/<int:pk>/",
        BroadcastSendView.as_view(),
        name="broadcast-send",
    ),
    path(
        "broadcast/send-test/<int:pk>/",
        BroadcastSendTestView.as_view(),
        name="broadcast-send-test",
    ),
    path(
        "broadcast/<int:pk>/",
        BroadcastDetailView.as_view(),
        name="broadcast-detail",
    ),
    path(
        "api/v1/broadcasts/<int:pk>/hero-image/",
        broadcast_hero_image_view,
        name="broadcast-hero-image",
    ),
]
