from django.contrib import admin

from .models import Donation


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ["order_id", "amount", "donor_name", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["order_id", "donor_name", "donor_email"]
    readonly_fields = ["id", "order_id", "bill_code", "toyyib_refno", "created_at"]
