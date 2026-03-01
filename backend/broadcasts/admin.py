from django.contrib import admin

from broadcasts.models import Broadcast, BroadcastRecipient


class BroadcastRecipientInline(admin.TabularInline):
    model = BroadcastRecipient
    extra = 0
    readonly_fields = ["subscriber", "email", "status", "brevo_message_id", "sent_at"]


@admin.register(Broadcast)
class BroadcastAdmin(admin.ModelAdmin):
    list_display = ["subject", "status", "recipient_count", "created_at", "sent_at"]
    list_filter = ["status"]
    readonly_fields = ["recipient_count", "created_at", "updated_at", "sent_at"]
    inlines = [BroadcastRecipientInline]


@admin.register(BroadcastRecipient)
class BroadcastRecipientAdmin(admin.ModelAdmin):
    list_display = ["email", "broadcast", "status", "sent_at"]
    list_filter = ["status"]
    readonly_fields = ["broadcast", "subscriber", "email", "brevo_message_id", "sent_at"]
