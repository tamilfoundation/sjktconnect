from django.contrib import admin

from .models import OutreachEmail, SchoolImage


@admin.register(SchoolImage)
class SchoolImageAdmin(admin.ModelAdmin):
    list_display = ["school", "source", "is_primary", "created_at"]
    list_filter = ["source", "is_primary"]
    search_fields = ["school__moe_code", "school__name"]


@admin.register(OutreachEmail)
class OutreachEmailAdmin(admin.ModelAdmin):
    list_display = ["school", "recipient_email", "status", "sent_at", "created_at"]
    list_filter = ["status"]
    search_fields = ["school__moe_code", "recipient_email"]
