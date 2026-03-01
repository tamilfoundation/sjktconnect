from django.urls import path

from . import views

app_name = "subscribers-api"

urlpatterns = [
    path("subscribe/", views.SubscribeView.as_view(), name="subscribe"),
    path(
        "unsubscribe/<uuid:token>/",
        views.UnsubscribeView.as_view(),
        name="unsubscribe",
    ),
    path(
        "preferences/<uuid:token>/",
        views.PreferencesView.as_view(),
        name="preferences",
    ),
]
