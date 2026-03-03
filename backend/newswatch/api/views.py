from django.db import connection
from django.db.models import Q
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination

from newswatch.api.serializers import NewsArticleSerializer
from newswatch.models import NewsArticle


class NewsListPagination(PageNumberPagination):
    page_size_query_param = "page_size"


class NewsListView(ListAPIView):
    """Public endpoint: paginated list of approved, analysed news articles."""

    serializer_class = NewsArticleSerializer
    authentication_classes = []
    permission_classes = []
    pagination_class = NewsListPagination

    def get_queryset(self):
        qs = NewsArticle.objects.filter(
            review_status="APPROVED",
            status="ANALYSED",
        ).order_by("-published_date", "-created_at")

        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(title__icontains=search) | Q(ai_summary__icontains=search)
            )

        category = self.request.query_params.get("category")
        if category == "school":
            # Articles with non-empty mentioned_schools
            qs = qs.exclude(mentioned_schools=[])
        elif category == "general":
            # Articles with empty mentioned_schools
            qs = qs.filter(mentioned_schools=[])

        return qs


class SchoolNewsView(ListAPIView):
    """Public endpoint: approved news articles mentioning a school."""

    serializer_class = NewsArticleSerializer
    authentication_classes = []
    permission_classes = []
    pagination_class = None

    def get_queryset(self):
        moe_code = self.kwargs["moe_code"]
        qs = NewsArticle.objects.filter(
            review_status="APPROVED",
            status="ANALYSED",
        )
        if connection.vendor == "postgresql":
            qs = qs.filter(
                mentioned_schools__contains=[{"moe_code": moe_code}],
            )
        else:
            # SQLite fallback: search JSON text for the moe_code value
            qs = qs.extra(
                where=["mentioned_schools LIKE %s"],
                params=[f'%"moe_code": "{moe_code}"%'],
            )
        return qs.order_by("-published_date", "-created_at")
