# diagnostic/admin.py
from django.contrib import admin
from .models import DiagnosticLead


@admin.register(DiagnosticLead)
class DiagnosticLeadAdmin(admin.ModelAdmin):
    list_display = ("email", "full_name", "organization", "version", "created_at")
    list_filter = ("version", "created_at")
    search_fields = ("email", "full_name", "organization")

    # IMPORTANT: do NOT use distinct("email") with ordering that starts with created_at
    ordering = ("email", "-created_at")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # One row per email (latest created_at) – Postgres-safe:
        return qs.order_by("email", "-created_at").distinct("email")
