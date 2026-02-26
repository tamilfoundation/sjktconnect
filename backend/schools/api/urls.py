"""API URL configuration for schools app."""

from django.urls import path

from schools.api.views import (
    ConstituencyGeoJSONDetailView,
    ConstituencyGeoJSONView,
    DUNGeoJSONDetailView,
    DUNGeoJSONView,
)

app_name = "schools-api"

urlpatterns = [
    path(
        "constituencies/geojson/",
        ConstituencyGeoJSONView.as_view(),
        name="constituency-geojson-list",
    ),
    path(
        "constituencies/<str:code>/geojson/",
        ConstituencyGeoJSONDetailView.as_view(),
        name="constituency-geojson-detail",
    ),
    path(
        "duns/geojson/",
        DUNGeoJSONView.as_view(),
        name="dun-geojson-list",
    ),
    path(
        "duns/<int:pk>/geojson/",
        DUNGeoJSONDetailView.as_view(),
        name="dun-geojson-detail",
    ),
]
