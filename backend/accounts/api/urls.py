"""API URL configuration for accounts app."""

from django.urls import path

from .views import (
    AdminUserDetailView,
    AdminUserListView,
    GoogleAuthView,
    MeView,
)

app_name = "accounts-api"

urlpatterns = [
    path("me/", MeView.as_view(), name="me"),
    path("google/", GoogleAuthView.as_view(), name="google-auth"),
    path("admin/users/", AdminUserListView.as_view(), name="admin-user-list"),
    path("admin/users/<int:pk>/", AdminUserDetailView.as_view(), name="admin-user-detail"),
]
