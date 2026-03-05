from django.contrib import admin

from .models import MP, MPScorecard, SittingBrief


@admin.register(MP)
class MPAdmin(admin.ModelAdmin):
    list_display = ["name", "constituency", "party", "email", "phone"]
    list_filter = ["party"]
    search_fields = ["name", "constituency__code", "constituency__name"]
    raw_id_fields = ["constituency"]


@admin.register(MPScorecard)
class MPScorecardAdmin(admin.ModelAdmin):
    list_display = [
        "mp_name", "constituency", "party", "total_mentions",
        "substantive_mentions", "questions_asked", "last_mention_date",
    ]
    list_filter = ["party"]
    search_fields = ["mp_name", "constituency__name"]
    raw_id_fields = ["constituency"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(SittingBrief)
class SittingBriefAdmin(admin.ModelAdmin):
    list_display = ["sitting", "title", "is_published", "published_at"]
    list_filter = ["is_published"]
    search_fields = ["title"]
    raw_id_fields = ["sitting"]
    readonly_fields = ["created_at", "updated_at"]
