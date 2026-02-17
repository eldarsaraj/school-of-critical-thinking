# diagnostic/admin.py

from django.contrib import admin
from django.http import HttpResponse
import csv

from .models import DiagnosticLead
from .management.commands.diagnostic_report import (
    build_report_rows,
)


@admin.register(DiagnosticLead)
class DiagnosticLeadAdmin(admin.ModelAdmin):
    list_display = ("email", "full_name", "organization", "version", "created_at")
    list_filter = ("version", "created_at")
    search_fields = ("email", "full_name", "organization")
    ordering = ("-created_at",)

    actions = ["download_module_report_csv", "download_dimension_report_csv"]

    @admin.action(description="Download module report CSV (aggregated)")
    def download_module_report_csv(self, request, queryset):
        return self._download_csv(map_version="v0_1", fmt="module")

    @admin.action(description="Download dimension report CSV (aggregated)")
    def download_dimension_report_csv(self, request, queryset):
        return self._download_csv(map_version="v0_1", fmt="dimension")

    def _download_csv(self, map_version: str, fmt: str):
        rows, fieldnames = build_report_rows(map_version=map_version, agg=fmt)

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="diagnostic_{fmt}_report.csv"'
        )

        writer = csv.DictWriter(response, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

        return response
