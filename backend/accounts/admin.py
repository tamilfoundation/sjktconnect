from django.contrib import admin

from .models import MagicLinkToken, SchoolContact, UserProfile


@admin.register(SchoolContact)
class SchoolContactAdmin(admin.ModelAdmin):
    list_display = ["email", "school", "name", "role", "is_active", "verified_at"]
    list_filter = ["is_active", "school__state"]
    search_fields = ["email", "name", "school__short_name", "school__moe_code"]
    readonly_fields = ["verified_at", "last_login", "created_at", "updated_at"]


@admin.register(MagicLinkToken)
class MagicLinkTokenAdmin(admin.ModelAdmin):
    list_display = ["email", "school", "is_used", "expires_at", "created_at"]
    list_filter = ["is_used"]
    search_fields = ["email", "school__moe_code"]
    readonly_fields = ["token", "created_at", "used_at"]


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ["display_name", "user", "role", "admin_school", "points", "is_active"]
    list_filter = ["role", "is_active"]
    search_fields = ["display_name", "user__email", "google_id"]
    raw_id_fields = ["user", "admin_school"]
