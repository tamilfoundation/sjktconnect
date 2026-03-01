from django.contrib import admin

from newswatch.models import NewsArticle


@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = [
        "title_short",
        "source_name",
        "status",
        "published_date",
        "created_at",
    ]
    list_filter = ["status", "source_name"]
    search_fields = ["title", "url", "body_text"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]

    @admin.display(description="Title")
    def title_short(self, obj):
        return obj.title[:80] if obj.title else "—"
