from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import path

from broadcasts.models import Broadcast
from broadcasts.views import (
    BroadcastComposeView,
    BroadcastDetailView,
    BroadcastListView,
    BroadcastPreviewView,
    BroadcastSendView,
)


def broadcast_hero_image_view(request, pk):
    """Serve the broadcast hero image as a PNG."""
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
