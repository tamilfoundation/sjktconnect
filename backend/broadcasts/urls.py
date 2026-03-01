from django.urls import path

from broadcasts.views import (
    BroadcastComposeView,
    BroadcastDetailView,
    BroadcastListView,
    BroadcastPreviewView,
    BroadcastSendView,
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
]
