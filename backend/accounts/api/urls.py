"""API URL configuration for accounts app."""

from django.urls import path

from .views import GoogleAuthView, MeView

app_name = "accounts-api"

urlpatterns = [
    path("me/", MeView.as_view(), name="me"),
    path("google/", GoogleAuthView.as_view(), name="google-auth"),
]
