from django.contrib import admin

from .models import Subscriber, SubscriptionPreference


class SubscriptionPreferenceInline(admin.TabularInline):
    model = SubscriptionPreference
    extra = 0


@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ["email", "name", "organisation", "is_active", "subscribed_at"]
    list_filter = ["is_active"]
    search_fields = ["email", "name", "organisation"]
    inlines = [SubscriptionPreferenceInline]
    readonly_fields = ["unsubscribe_token", "subscribed_at", "unsubscribed_at"]


@admin.register(SubscriptionPreference)
class SubscriptionPreferenceAdmin(admin.ModelAdmin):
    list_display = ["subscriber", "category", "is_enabled"]
    list_filter = ["category", "is_enabled"]
