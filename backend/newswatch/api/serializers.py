from rest_framework import serializers

from newswatch.models import NewsArticle


class NewsArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsArticle
        fields = [
            "id",
            "title",
            "url",
            "source_name",
            "published_date",
            "ai_summary",
            "sentiment",
            "is_urgent",
            "urgent_reason",
            "created_at",
        ]
