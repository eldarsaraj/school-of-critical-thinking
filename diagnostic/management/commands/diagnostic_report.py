from __future__ import annotations

import csv
import sys
from collections import Counter, defaultdict
from dataclasses import asdict
from typing import Dict, Iterable, List, Tuple

from django.core.management.base import BaseCommand

from diagnostic.models import DiagnosticLead
from diagnostic.reporting_map import load_reporting_map


def _split_codes(module_ids: str) -> List[str]:
    # module_ids stored like: "UH_PU,MA_AB" (maybe with spaces) or ""
    if not module_ids:
        return []
    return [p.strip() for p in module_ids.split(",") if p.strip()]


class Command(BaseCommand):
    help = "Aggregate DiagnosticLead.module_ids into counts by module/dimension/breakpoint and output CSV."

    def add_arguments(self, parser):
        parser.add_argument(
            "--version",
            default="v0_1",
            help="Reporting map version (expects diagnostic/reporting_map_<version>.yaml). Default: v0_1",
        )
        parser.add_argument(
            "--format",
            choices=["module", "dimension", "breakpoint"],
            default="module",
            help="Aggregation level. Default: module",
        )

    def handle(self, *args, **opts):
        map_version = opts["version"]
        agg = opts["format"]

        version, by_id = load_reporting_map(map_version)

        # Count module codes across all leads
        counts = Counter()
        for s in DiagnosticLead.objects.values_list("module_ids", flat=True).iterator():
            for code in _split_codes(s or ""):
                counts[code] += 1

        # Build rows
        rows: List[Dict[str, object]] = []

        if agg == "module":
            for code, c in counts.most_common():
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

            fieldnames = [
                "map_version",
                "code",
                "dimension",
                "breakpoint",
                "title",
                "count",
            ]

        elif agg == "dimension":
            dim_counts = Counter()
            for code, c in counts.items():
                meta = by_id.get(code)
                dim = meta.dimension if meta else "UNKNOWN"
                dim_counts[dim] += c

            for dim, c in dim_counts.most_common():
                rows.append({"map_version": version, "dimension": dim, "count": c})

            fieldnames = ["map_version", "dimension", "count"]

        else:  # breakpoint
            bp_counts = Counter()
            bp_dim = {}
            for code, c in counts.items():
                meta = by_id.get(code)
                if meta:
                    key = meta.breakpoint
                    bp_dim[key] = meta.dimension
                else:
                    key = "UNKNOWN"
                    bp_dim[key] = "UNKNOWN"
                bp_counts[key] += c

            for bp, c in bp_counts.most_common():
                rows.append(
                    {
                        "map_version": version,
                        "dimension": bp_dim.get(bp, "UNKNOWN"),
                        "breakpoint": bp,
                        "count": c,
                    }
                )

            fieldnames = ["map_version", "dimension", "breakpoint", "count"]

        writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
