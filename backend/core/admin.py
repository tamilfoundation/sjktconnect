from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "action", "target_type", "target_id", "user", "ip_address")
    list_filter = ("action", "target_type")
    search_fields = ("target_id", "target_type")
    readonly_fields = ("timestamp", "user", "action", "target_type", "target_id", "detail", "ip_address")
    ordering = ("-timestamp",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
