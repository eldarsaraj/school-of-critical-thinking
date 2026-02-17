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


from pathlib import Path
from typing import Tuple, Dict, Union
import yaml


def load_reporting_map(
    path_or_version: Union[str, Path] = DEFAULT_MAP_PATH,
) -> Tuple[str, Dict[str, ModuleMeta]]:
    """
    Accepts either:
      - a Path / path string to a YAML file, OR
      - a version string like "v0_1" (loads reporting_map_<version>.yaml next to this file)

    Returns (version, modules_by_id).
    """
    base_dir = Path(__file__).resolve().parent

    # Normalize input
    if isinstance(path_or_version, Path):
        path = path_or_version
    else:
        s = str(path_or_version).strip()

        # Treat "v0_1" / "v1_2" / etc as a version, not a filename
        if s.startswith("v") and "." not in s and "/" not in s and "\\" not in s:
            path = base_dir / f"reporting_map_{s}.yaml"
        else:
            path = Path(s)

    # Resolve relative paths relative to this module file
    if not path.is_absolute():
        path = base_dir / path

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    version = (data.get("version") or "unknown").strip()
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
