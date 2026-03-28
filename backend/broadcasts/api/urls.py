from django.urls import path

from . import views

app_name = "broadcasts-api"

urlpatterns = [
    path(
        "webhooks/brevo/",
        views.BrevoWebhookView.as_view(),
        name="brevo-webhook",
    ),
]
