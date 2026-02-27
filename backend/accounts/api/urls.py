"""API URL configuration for accounts app."""

from django.urls import path

from .views import MeView, RequestMagicLinkView, VerifyTokenView

app_name = "accounts-api"

urlpatterns = [
    path("request-magic-link/", RequestMagicLinkView.as_view(), name="request-magic-link"),
    path("verify/<str:token>/", VerifyTokenView.as_view(), name="verify-token"),
    path("me/", MeView.as_view(), name="me"),
]
