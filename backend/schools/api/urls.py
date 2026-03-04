"""API URL configuration for schools app."""

from django.urls import include, path

from newswatch.api.views import NewsListView, SchoolNewsView
from parliament.api.views import SchoolMentionsView
from schools.api.views import (
    ConstituencyDetailView,
    ConstituencyGeoJSONDetailView,
    ConstituencyGeoJSONView,
    ConstituencyListView,
    ContactFormView,
    DUNDetailView,
    DUNGeoJSONDetailView,
    DUNGeoJSONView,
    DUNListView,
    NationalStatsView,
    SchoolConfirmView,
    SchoolDetailView,
    SchoolEditView,
    SchoolListView,
    SearchView,
    duitnow_qr,
)

app_name = "schools-api"

urlpatterns = [
    # Schools — edit/confirm before detail (sub-paths before bare <str:moe_code>)
    path("schools/", SchoolListView.as_view(), name="school-list"),
    path("schools/<str:moe_code>/edit/", SchoolEditView.as_view(), name="school-edit"),
    path("schools/<str:moe_code>/confirm/", SchoolConfirmView.as_view(), name="school-confirm"),
    path("schools/<str:moe_code>/mentions/", SchoolMentionsView.as_view(), name="school-mentions"),
    path("schools/<str:moe_code>/news/", SchoolNewsView.as_view(), name="school-news"),
    path("schools/<str:moe_code>/duitnow-qr/", duitnow_qr, name="duitnow-qr"),
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
    # Statistics
    path("stats/national/", NationalStatsView.as_view(), name="national-stats"),
    # Search
    path("search/", SearchView.as_view(), name="search"),
    # News (public list)
    path("news/", NewsListView.as_view(), name="news-list"),
    # Contact
    path("contact/", ContactFormView.as_view(), name="contact"),
    # Parliament (scorecards, briefs)
    path("", include("parliament.api.urls")),
]
