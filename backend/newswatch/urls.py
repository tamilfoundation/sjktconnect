from django.urls import path

from newswatch import views

app_name = "newswatch"

urlpatterns = [
    path(
        "dashboard/news/",
        views.NewsQueueView.as_view(),
        name="news-queue",
    ),
    path(
        "dashboard/news/<int:pk>/",
        views.NewsArticleDetailView.as_view(),
        name="news-detail",
    ),
    path(
        "dashboard/news/<int:pk>/approve/",
        views.ApproveArticleView.as_view(),
        name="news-approve",
    ),
    path(
        "dashboard/news/<int:pk>/reject/",
        views.RejectArticleView.as_view(),
        name="news-reject",
    ),
    path(
        "dashboard/news/<int:pk>/toggle-urgent/",
        views.ToggleUrgentView.as_view(),
        name="news-toggle-urgent",
    ),
]
