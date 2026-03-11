from django.urls import path

from community.api.views import school_suggestions_view

urlpatterns = [
    path(
        "schools/<str:moe_code>/suggestions/",
        school_suggestions_view,
        name="school-suggestions",
    ),
]
