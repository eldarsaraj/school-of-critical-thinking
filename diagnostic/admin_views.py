from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse

from .management.commands.diagnostic_report import (
    build_report_rows,
)  # adjust if your helper name differs


@staff_member_required
def diagnostic_admin_report_csv(request):
    map_version = request.GET.get("map_version", "v0_1")
    fmt = request.GET.get("format", "module")

    csv_text = build_report_rows(
        map_version=map_version, fmt=fmt
    )  # must return CSV string
    resp = HttpResponse(csv_text, content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = (
        f'attachment; filename="diagnostic_report_{map_version}_{fmt}.csv"'
    )
    return resp
