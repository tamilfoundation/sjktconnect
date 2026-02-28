"""Schools app URL configuration — admin/dashboard views."""

from django.urls import path

from schools.views import VerificationDashboardView

app_name = "schools"

urlpatterns = [
    path(
        "dashboard/verification/",
        VerificationDashboardView.as_view(),
        name="verification-dashboard",
    ),
]
