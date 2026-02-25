from django.contrib import admin

from .models import HansardMention, HansardSitting


@admin.register(HansardSitting)
class HansardSittingAdmin(admin.ModelAdmin):
    list_display = ["sitting_date", "status", "mention_count", "total_pages", "pdf_filename"]
    list_filter = ["status"]
    search_fields = ["pdf_filename"]
    readonly_fields = ["created_at"]


@admin.register(HansardMention)
class HansardMentionAdmin(admin.ModelAdmin):
    list_display = ["sitting", "page_number", "keyword_matched", "review_status"]
    list_filter = ["review_status", "keyword_matched"]
    search_fields = ["verbatim_quote", "keyword_matched"]
    readonly_fields = ["created_at", "updated_at"]
