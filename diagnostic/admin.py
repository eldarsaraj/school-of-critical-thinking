# diagnostic/admin.py
from django.contrib import admin
from django.db.models import F, Window
from django.db.models.functions import RowNumber

from .models import DiagnosticLead


@admin.register(DiagnosticLead)
class DiagnosticLeadAdmin(admin.ModelAdmin):
    list_display = ("email", "full_name", "organization", "version", "created_at")
    list_filter = ("version", "created_at")
    search_fields = ("email", "full_name", "organization")
    ordering = ("-created_at",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        # Latest lead per email without DISTINCT ON (Postgres-safe in admin/paginator)
        qs = qs.annotate(
            rn=Window(
                expression=RowNumber(),
                partition_by=[F("email")],
                order_by=F("created_at").desc(),
            )
        ).filter(rn=1)

        return qs
