from django.contrib import admin
from .models import ContactMessage


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
