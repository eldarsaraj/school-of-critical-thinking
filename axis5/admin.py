from django.contrib import admin
from django.utils.html import format_html
from .models import Item, Form, Session, Response, Result


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ["id", "email", "state", "form_version", "started_at", "completed_at", "has_result"]
    list_filter = ["state", "form_version"]
    search_fields = ["email"]
    readonly_fields = ["token", "started_at", "completed_at", "ip_hash", "user_agent"]
    ordering = ["-started_at"]

    def has_result(self, obj):
        try:
            obj.result
            return format_html('<span style="color:#5aab8c;">&#10003;</span>')
        except Result.DoesNotExist:
            return format_html('<span style="color:#c4635b;">&#8722;</span>')
    has_result.short_description = "Result"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("result")


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ["id", "session_email", "scoring_version", "form_version", "computed_at", "quality_flags_display"]
    list_filter = ["scoring_version", "form_version"]
    readonly_fields = ["session", "form_version", "scoring_version", "payload", "quality_flags", "computed_at"]
    ordering = ["-computed_at"]

    def session_email(self, obj):
        return obj.session.email
    session_email.short_description = "Email"

    def quality_flags_display(self, obj):
        if not obj.quality_flags:
            return "—"
        return ", ".join(obj.quality_flags)
    quality_flags_display.short_description = "Flags"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("session")


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ["item_id", "dimension", "format", "tier", "domain", "form_version", "scored", "field_test", "active", "position"]
    list_filter = ["dimension", "format", "form_version", "active", "scored", "field_test"]
    search_fields = ["item_id", "tag", "domain"]
    ordering = ["form_version", "position"]
    readonly_fields = ["payload"]


@admin.register(Form)
class FormAdmin(admin.ModelAdmin):
    list_display = ["form_id", "form_version", "scoring_version", "active"]
    list_filter = ["active"]


@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):
    list_display = ["id", "session_id", "item_id_display", "ms_total", "n_changes", "created_at"]
    list_filter = ["item__dimension", "item__format"]
    readonly_fields = ["session", "item", "value", "ms_first", "ms_total", "n_changes", "created_at"]
    ordering = ["-created_at"]

    def item_id_display(self, obj):
        return obj.item.item_id
    item_id_display.short_description = "Item"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("session", "item")
