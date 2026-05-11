from django.contrib import admin

from broadcasts.models import Broadcast, BroadcastRecipient


class BroadcastRecipientInline(admin.TabularInline):
    model = BroadcastRecipient
    extra = 0
    readonly_fields = ["subscriber", "email", "status", "brevo_message_id", "sent_at"]


@admin.register(Broadcast)
class BroadcastAdmin(admin.ModelAdmin):
    list_display = [
        "subject", "kind", "coverage", "status", "recipient_count",
        "created_at", "sent_at",
    ]
    list_filter = ["status", "kind"]
    readonly_fields = ["recipient_count", "created_at", "updated_at", "sent_at"]
    inlines = [BroadcastRecipientInline]

    @admin.display(description="Coverage")
    def coverage(self, obj):
        if obj.coverage_start_date and obj.coverage_end_date:
            return f"{obj.coverage_start_date} \u2192 {obj.coverage_end_date}"
        return "\u2014"


@admin.register(BroadcastRecipient)
class BroadcastRecipientAdmin(admin.ModelAdmin):
    list_display = ["email", "broadcast", "status", "sent_at"]
    list_filter = ["status"]
    readonly_fields = ["broadcast", "subscriber", "email", "brevo_message_id", "sent_at"]
