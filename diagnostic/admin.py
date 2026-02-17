# diagnostic/admin.py
from django.contrib import admin
from .models import DiagnosticLead


@admin.register(DiagnosticLead)
class DiagnosticLeadAdmin(admin.ModelAdmin):
    list_display = ("email", "full_name", "organization", "version", "created_at")
    list_filter = ("version", "created_at")
    search_fields = ("email", "full_name", "organization")

    # Lock sorting so Postgres DISTINCT ON stays valid.
    ordering = ("email", "-created_at")
    sortable_by = ()  # disables clicking column headers to change ORDER BY

    def get_ordering(self, request):
        # extra lock: admin must always order starting with "email"
        return ("email", "-created_at")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Latest row per email (Postgres-safe DISTINCT ON)
        return qs.order_by("email", "-created_at").distinct("email")
