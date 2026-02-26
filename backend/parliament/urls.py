from django.urls import path

from . import views

app_name = "parliament"

urlpatterns = [
    # Admin review (login required)
    path(
        "review/",
        views.ReviewQueueView.as_view(),
        name="review-queue",
    ),
    path(
        "review/<int:sitting_pk>/",
        views.SittingReviewView.as_view(),
        name="sitting-review",
    ),
    path(
        "review/mention/<int:pk>/",
        views.MentionDetailView.as_view(),
        name="mention-detail",
    ),
    path(
        "review/mention/<int:pk>/approve/",
        views.ApproveMentionView.as_view(),
        name="mention-approve",
    ),
    path(
        "review/mention/<int:pk>/reject/",
        views.RejectMentionView.as_view(),
        name="mention-reject",
    ),
    path(
        "review/<int:sitting_pk>/publish/",
        views.PublishBriefView.as_view(),
        name="publish-brief",
    ),
    # Public views
    path(
        "parliament-watch/",
        views.ParliamentWatchView.as_view(),
        name="watch",
    ),
    path(
        "parliament-watch/<str:sitting_date>/",
        views.BriefDetailView.as_view(),
        name="brief-detail",
    ),
]
