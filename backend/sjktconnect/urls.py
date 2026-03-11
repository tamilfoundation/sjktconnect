from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.http import JsonResponse
from django.urls import include, path


def health_check(_request):
    """Health check endpoint for Cloud Run."""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("health/", health_check, name="health-check"),
    path("admin/", admin.site.urls),
    path("api/v1/", include("schools.api.urls")),
    path("api/v1/auth/", include("accounts.api.urls")),
    path("api/v1/subscribers/", include("subscribers.api.urls")),
    path("accounts/login/", auth_views.LoginView.as_view(), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", include("broadcasts.urls")),
    path("", include("schools.urls")),
    path("", include("parliament.urls")),
    path("", include("newswatch.urls")),
    path("api/v1/donations/", include("donations.api.urls")),
    path("api/v1/", include("community.api.urls")),
]
