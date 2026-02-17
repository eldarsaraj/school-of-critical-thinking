# diagnostic/admin.py
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import reverse

from .models import DiagnosticLead


@admin.register(DiagnosticLead)
class DiagnosticLeadAdmin(admin.ModelAdmin):
    list_display = ("email", "full_name", "organization", "version", "created_at")
    list_filter = ("version", "created_at")
    search_fields = ("email", "full_name", "organization")
    ordering = ("-created_at",)

    actions = ["download_module_report_csv", "download_dimension_report_csv"]

    @admin.action(description="Download module report CSV (aggregated)")
    def download_module_report_csv(self, request, queryset):
        url = reverse("diagnostic_admin_report_csv") + "?map_version=v0_1&format=module"
        return HttpResponseRedirect(url)

    @admin.action(description="Download dimension report CSV (aggregated)")
    def download_dimension_report_csv(self, request, queryset):
        url = (
            reverse("diagnostic_admin_report_csv")
            + "?map_version=v0_1&format=dimension"
        )
        return HttpResponseRedirect(url)
