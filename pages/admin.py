from django.contrib import admin
from .models import ContactMessage, CurriculumLead


@admin.register(CurriculumLead)
class CurriculumLeadAdmin(admin.ModelAdmin):
    list_display = ("email", "source", "created_at")
    list_filter = ("source", "created_at")
    search_fields = ("email",)
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "submitted_at", "path", "source")
    list_filter = ("submitted_at", "path", "source")
    search_fields = ("name", "email", "message", "path", "source")
    readonly_fields = ("submitted_at", "path", "source")

    fieldsets = (
        (None, {"fields": ("name", "email", "message")}),
        ("Context", {"fields": ("path", "source", "submitted_at")}),
    )
