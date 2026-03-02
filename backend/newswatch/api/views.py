from django.db import connection
from rest_framework.generics import ListAPIView

from newswatch.api.serializers import NewsArticleSerializer
from newswatch.models import NewsArticle


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
