from django.contrib import admin

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ["display_name", "user", "role", "admin_school", "points", "is_active"]
    list_filter = ["role", "is_active"]
    search_fields = ["display_name", "user__email", "google_id"]
    raw_id_fields = ["user", "admin_school"]
