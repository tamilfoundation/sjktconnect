from django.contrib import admin

from .models import Constituency, DUN, School, SchoolLeader


@admin.register(Constituency)
class ConstituencyAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "state", "mp_name", "mp_party")
    list_filter = ("state",)
    search_fields = ("code", "name", "mp_name")
    ordering = ("code",)


@admin.register(DUN)
class DUNAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "constituency", "state", "adun_name")
    list_filter = ("state", "constituency")
    search_fields = ("code", "name", "adun_name")
    ordering = ("constituency__code", "code")


class SchoolLeaderInline(admin.TabularInline):
    model = SchoolLeader
    extra = 0
    fields = ("role", "name", "phone", "email", "is_active")


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ("moe_code", "short_name", "state", "ppd", "enrolment", "teacher_count", "is_active")
    list_filter = ("state", "is_active", "gps_verified", "skm_eligible")
    search_fields = ("moe_code", "name", "short_name")
    ordering = ("moe_code",)
    readonly_fields = ("created_at", "updated_at")
    inlines = [SchoolLeaderInline]
