from django.urls import path

from community.api.views import (
    approve_suggestion_view,
    pending_suggestions_view,
    reject_suggestion_view,
    school_suggestions_view,
    suggestion_image_view,
)

urlpatterns = [
    path(
        "schools/<str:moe_code>/suggestions/",
        school_suggestions_view,
        name="school-suggestions",
    ),
    path(
        "suggestions/pending/",
        pending_suggestions_view,
        name="suggestions-pending",
    ),
    path(
        "suggestions/<int:pk>/approve/",
        approve_suggestion_view,
        name="suggestion-approve",
    ),
    path(
        "suggestions/<int:pk>/reject/",
        reject_suggestion_view,
        name="suggestion-reject",
    ),
    path(
        "suggestions/<int:pk>/image/",
        suggestion_image_view,
        name="suggestion-image",
    ),
]
