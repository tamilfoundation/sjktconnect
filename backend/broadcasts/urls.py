from django.urls import path

from broadcasts.views import (
    BroadcastComposeView,
    BroadcastListView,
    BroadcastPreviewView,
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
]
