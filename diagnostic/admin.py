# diagnostic/admin.py
from __future__ import annotations

import csv

from django.contrib import admin
from django.http import HttpResponse

from .models import DiagnosticLead
from .reporting_map import load_reporting_map


def _split_codes(module_ids: str) -> list[str]:
    if not module_ids:
        return []
    return [p.strip() for p in module_ids.split(",") if p.strip()]


def _build_rows(*, map_version: str, agg: str) -> tuple[str, list[dict]]:
    version, by_id = load_reporting_map(map_version)

    # Count module codes across all leads
    counts: dict[str, int] = {}
    for s in DiagnosticLead.objects.values_list("module_ids", flat=True).iterator():
        for code in _split_codes(s or ""):
            counts[code] = counts.get(code, 0) + 1

    # Sort like Counter.most_common()
    items = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)

    rows: list[dict] = []

    if agg == "module":
        for code, c in items:
            meta = by_id.get(code)
            if meta is None:
                rows.append(
                    {
                        "map_version": version,
                        "code": code,
                        "dimension": "UNKNOWN",
                        "breakpoint": "UNKNOWN",
                        "title": "",
                        "count": c,
                    }
                )
            else:
                rows.append(
                    {
                        "map_version": version,
                        "code": code,
                        "dimension": meta.dimension,
                        "breakpoint": meta.breakpoint,
                        "title": meta.title,
                        "count": c,
                    }
                )
        return version, rows

    if agg == "dimension":
        dim_counts: dict[str, int] = {}
        for code, c in counts.items():
            meta = by_id.get(code)
            dim = meta.dimension if meta else "UNKNOWN"
            dim_counts[dim] = dim_counts.get(dim, 0) + c

        for dim, c in sorted(dim_counts.items(), key=lambda kv: kv[1], reverse=True):
            rows.append({"map_version": version, "dimension": dim, "count": c})
        return version, rows

    # breakpoint
    bp_counts: dict[str, int] = {}
    bp_dim: dict[str, str] = {}
    for code, c in counts.items():
        meta = by_id.get(code)
        if meta:
            bp = meta.breakpoint
            bp_dim[bp] = meta.dimension
        else:
            bp = "UNKNOWN"
            bp_dim[bp] = "UNKNOWN"
        bp_counts[bp] = bp_counts.get(bp, 0) + c

    for bp, c in sorted(bp_counts.items(), key=lambda kv: kv[1], reverse=True):
        rows.append(
            {
                "map_version": version,
                "dimension": bp_dim.get(bp, "UNKNOWN"),
                "breakpoint": bp,
                "count": c,
            }
        )
    return version, rows


def _csv_response(
    rows: list[dict], fieldnames: list[str], filename: str
) -> HttpResponse:
    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    writer = csv.DictWriter(resp, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return resp


@admin.register(DiagnosticLead)
class DiagnosticLeadAdmin(admin.ModelAdmin):
    list_display = ("email", "full_name", "organization", "version", "created_at")
    list_filter = ("version", "created_at")
    search_fields = ("email", "full_name", "organization")
    ordering = ("-created_at",)

    actions = [
        "download_module_report_csv",
        "download_dimension_report_csv",
        "download_breakpoint_report_csv",
    ]

    @admin.action(description="Download module report CSV (aggregated)")
    def download_module_report_csv(self, request, queryset):
        map_version = request.GET.get("map_version", "v0_1")
        _, rows = _build_rows(map_version=map_version, agg="module")
        fieldnames = [
            "map_version",
            "code",
            "dimension",
            "breakpoint",
            "title",
            "count",
        ]
        return _csv_response(
            rows, fieldnames, f"diagnostic_report_{map_version}_module.csv"
        )

    @admin.action(description="Download dimension report CSV (aggregated)")
    def download_dimension_report_csv(self, request, queryset):
        map_version = request.GET.get("map_version", "v0_1")
        _, rows = _build_rows(map_version=map_version, agg="dimension")
        fieldnames = ["map_version", "dimension", "count"]
        return _csv_response(
            rows, fieldnames, f"diagnostic_report_{map_version}_dimension.csv"
        )

    @admin.action(description="Download breakpoint report CSV (aggregated)")
    def download_breakpoint_report_csv(self, request, queryset):
        map_version = request.GET.get("map_version", "v0_1")
        _, rows = _build_rows(map_version=map_version, agg="breakpoint")
        fieldnames = ["map_version", "dimension", "breakpoint", "count"]
        return _csv_response(
            rows, fieldnames, f"diagnostic_report_{map_version}_breakpoint.csv"
        )
