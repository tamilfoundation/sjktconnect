from django.contrib import admin

from feedback.models import InboundEmail


@admin.register(InboundEmail)
class InboundEmailAdmin(admin.ModelAdmin):
    list_display = [
        "from_email",
        "subject_short",
        "classification",
        "source_broadcast_type",
        "response_status",
        "escalated",
        "received_at",
    ]
    list_filter = [
        "classification",
        "response_status",
        "escalated",
        "source_broadcast_type",
    ]
    search_fields = ["from_email", "from_name", "subject", "body_text"]
    readonly_fields = [
        "gmail_message_id",
        "gmail_thread_id",
        "received_at",
        "classification_reasoning",
    ]
    ordering = ["-received_at"]

    @admin.display(description="Subject")
    def subject_short(self, obj):
        return obj.subject[:80] if obj.subject else "—"
