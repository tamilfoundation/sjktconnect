"""API URL configuration for parliament app."""

from django.urls import path

from parliament.api.views import (
    AllMentionsListView,
    MeetingReportDetailView,
    MeetingReportListView,
    MPScorecardDetailView,
    MPScorecardListView,
    SittingBriefDetailView,
    SittingBriefListView,
)

app_name = "parliament-api"

urlpatterns = [
    path(
        "scorecards/",
        MPScorecardListView.as_view(),
        name="scorecard-list",
    ),
    path(
        "scorecards/<int:pk>/",
        MPScorecardDetailView.as_view(),
        name="scorecard-detail",
    ),
    path(
        "briefs/",
        SittingBriefListView.as_view(),
        name="brief-list",
    ),
    path(
        "briefs/<int:pk>/",
        SittingBriefDetailView.as_view(),
        name="brief-detail",
    ),
    path(
        "meetings/",
        MeetingReportListView.as_view(),
        name="meeting-list",
    ),
    path(
        "meetings/<int:pk>/",
        MeetingReportDetailView.as_view(),
        name="meeting-detail",
    ),
    path(
        "mentions/",
        AllMentionsListView.as_view(),
        name="mention-list",
    ),
]
