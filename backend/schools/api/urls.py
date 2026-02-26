"""API URL configuration for schools app."""

from django.urls import include, path

from schools.api.views import (
    ConstituencyDetailView,
    ConstituencyGeoJSONDetailView,
    ConstituencyGeoJSONView,
    ConstituencyListView,
    DUNDetailView,
    DUNGeoJSONDetailView,
    DUNGeoJSONView,
    DUNListView,
    SchoolDetailView,
    SchoolListView,
    SearchView,
)

app_name = "schools-api"

urlpatterns = [
    # Schools
    path("schools/", SchoolListView.as_view(), name="school-list"),
    path("schools/<str:moe_code>/", SchoolDetailView.as_view(), name="school-detail"),
    # Constituencies — GeoJSON before detail (geojson/ is a literal, not a <str:code>)
    path("constituencies/", ConstituencyListView.as_view(), name="constituency-list"),
    path("constituencies/geojson/", ConstituencyGeoJSONView.as_view(), name="constituency-geojson-list"),
    path("constituencies/<str:code>/geojson/", ConstituencyGeoJSONDetailView.as_view(), name="constituency-geojson-detail"),
    path("constituencies/<str:code>/", ConstituencyDetailView.as_view(), name="constituency-detail"),
    # DUNs — GeoJSON before detail
    path("duns/", DUNListView.as_view(), name="dun-list"),
    path("duns/geojson/", DUNGeoJSONView.as_view(), name="dun-geojson-list"),
    path("duns/<int:pk>/geojson/", DUNGeoJSONDetailView.as_view(), name="dun-geojson-detail"),
    path("duns/<int:pk>/", DUNDetailView.as_view(), name="dun-detail"),
    # Search
    path("search/", SearchView.as_view(), name="search"),
    # Parliament (scorecards, briefs)
    path("", include("parliament.api.urls")),
]
