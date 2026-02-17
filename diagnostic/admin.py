# diagnostic/admin.py
from django.contrib import admin
from .models import DiagnosticLead


@admin.register(DiagnosticLead)
class DiagnosticLeadAdmin(admin.ModelAdmin):
    list_display = ("email", "full_name", "organization", "version", "created_at")
    list_filter = ("version", "created_at")
    search_fields = ("email", "full_name", "organization")
    ordering = ("-created_at",)

    # Show only the newest row per email (unique emails)
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Postgres-specific DISTINCT ON (works on Heroku Postgres)
        return qs.order_by("email", "-created_at").distinct("email")
