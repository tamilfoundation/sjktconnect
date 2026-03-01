from django.contrib import admin

from newswatch.models import NewsArticle


@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = [
        "title_short",
        "source_name",
        "status",
        "relevance_score",
        "sentiment",
        "is_urgent",
        "review_status",
        "published_date",
        "created_at",
    ]
    list_filter = ["status", "source_name", "sentiment", "review_status", "is_urgent"]
    search_fields = ["title", "url", "body_text", "ai_summary"]
    readonly_fields = ["created_at", "updated_at", "ai_raw_response"]
    ordering = ["-created_at"]

    @admin.display(description="Title")
    def title_short(self, obj):
        return obj.title[:80] if obj.title else "—"
