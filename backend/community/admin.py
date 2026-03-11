from django.contrib import admin
from community.models import Suggestion


@admin.register(Suggestion)
class SuggestionAdmin(admin.ModelAdmin):
    list_display = ["school", "user", "type", "status", "field_name", "created_at"]
    list_filter = ["type", "status"]
    readonly_fields = ["created_at", "updated_at"]
