from django.urls import path

from . import views

urlpatterns = [
    path("", views.create_donation, name="create-donation"),
    path("callback/", views.toyyib_callback, name="toyyib-callback"),
    path("status/", views.donation_status, name="donation-status"),
]
