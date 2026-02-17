# diagnostic/reporting_map.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple
from collections import Counter

import yaml


# Put your YAML file here (next to this python file):
# diagnostic/reporting_map_v0_1.yaml
DEFAULT_MAP_PATH = Path(__file__).with_name("reporting_map_v0_1.yaml")


@dataclass(frozen=True)
class ModuleMeta:
    code: str
    dimension: str
    breakpoint: str
    title: str


def parse_module_ids(module_ids: str) -> List[str]:
    """
    "UH_PU,MA_AB" -> ["UH_PU","MA_AB"]
    "" -> []
    """
    if not module_ids:
        return []
    parts = [p.strip() for p in module_ids.split(",")]
    return [p for p in parts if p]


def load_reporting_map(
    path: Path = DEFAULT_MAP_PATH,
) -> Tuple[str, Dict[str, ModuleMeta]]:
    """
    Loads the YAML and returns (version, modules_by_id).
    Unknown ids are handled later (they'll be counted under UNKNOWN).
    """

    # Ensure path is always a Path object (even if DEFAULT_MAP_PATH is a string)
    if not isinstance(path, Path):
        path = Path(path)

    # If relative path, resolve relative to this file
    if not path.is_absolute():
        path = Path(__file__).resolve().parent / path

    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    version = data.get("version", "unknown")
    modules = data.get("modules", []) or []

    by_id: Dict[str, ModuleMeta] = {}
    for m in modules:
        mid = (m.get("id") or "").strip()
        if not mid:
            continue
        by_id[mid] = ModuleMeta(
            code=mid,
            dimension=(m.get("dimension") or "UNKNOWN").strip(),
            breakpoint=(m.get("breakpoint") or "UNKNOWN").strip(),
            title=(m.get("title") or "").strip(),
        )

    return version, by_id


def aggregate_breakpoints(
    module_ids_strings: Iterable[str], *, map_path: Path = DEFAULT_MAP_PATH
) -> List[dict]:
    """
    One row per module id (breakpoint), with names pulled from YAML.
    """
    _, by_id = load_reporting_map(map_path)

    counts: Counter[str] = Counter()
    for s in module_ids_strings:
        for code in parse_module_ids(s):
            counts[code] += 1

    rows: List[dict] = []
    for code, n in counts.most_common():
        meta = by_id.get(code)
        rows.append(
            {
                "module_id": code,
                "dimension": meta.dimension if meta else "UNKNOWN",
                "breakpoint": meta.breakpoint if meta else "UNKNOWN",
                "title": meta.title if meta else "",
                "count": int(n),
            }
        )
    return rows


def aggregate_dimensions(
    module_ids_strings: Iterable[str], *, map_path: Path = DEFAULT_MAP_PATH
) -> List[dict]:
    """
    One row per dimension, summing all module occurrences in that dimension.
    """
    _, by_id = load_reporting_map(map_path)

    dim_counts: Counter[str] = Counter()
    for s in module_ids_strings:
        for code in parse_module_ids(s):
            meta = by_id.get(code)
            dim = meta.dimension if meta else "UNKNOWN"
            dim_counts[dim] += 1

    return [{"dimension": dim, "count": int(n)} for dim, n in dim_counts.most_common()]
