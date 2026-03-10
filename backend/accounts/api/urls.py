"""API URL configuration for accounts app."""

from django.urls import path

from .views import (
    GoogleAuthView,
    LinkSchoolView,
    MeView,
    RequestMagicLinkView,
    VerifyTokenView,
)

app_name = "accounts-api"

urlpatterns = [
    path("request-magic-link/", RequestMagicLinkView.as_view(), name="request-magic-link"),
    path("verify/<str:token>/", VerifyTokenView.as_view(), name="verify-token"),
    path("me/", MeView.as_view(), name="me"),
    path("google/", GoogleAuthView.as_view(), name="google-auth"),
    path("link-school/", LinkSchoolView.as_view(), name="link-school"),
]
