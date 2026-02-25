from django.contrib import admin

from .models import HansardMention, HansardSitting, MentionedSchool, SchoolAlias


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


@admin.register(SchoolAlias)
class SchoolAliasAdmin(admin.ModelAdmin):
    list_display = ["alias", "school", "alias_type", "alias_normalized"]
    list_filter = ["alias_type"]
    search_fields = ["alias", "alias_normalized", "school__short_name"]
    raw_id_fields = ["school"]


@admin.register(MentionedSchool)
class MentionedSchoolAdmin(admin.ModelAdmin):
    list_display = ["mention", "school", "matched_by", "confidence_score", "needs_review"]
    list_filter = ["matched_by", "needs_review"]
    search_fields = ["school__short_name", "matched_text"]
    raw_id_fields = ["mention", "school"]
