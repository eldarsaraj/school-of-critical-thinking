# ---------------------------------------------------------------------------
# SHSAT Scoring
# ---------------------------------------------------------------------------
#
# Two scoring systems:
#
# 1. scale_score(raw)  — legacy, used for manual score logging only.
#    Maps 0-47 correct to a section score. Intentionally conservative.
#
# 2. scale_score_adaptive(raw, module)  — used for adaptive tests.
#    Maps 0-57 correct → section score (200-400), with two separate curves:
#      'hard' module: more generous (harder questions deserve more credit)
#      'easy' module: more conservative
#
# Calibration for adaptive tables (Option B):
#   Hard path, ~23/57 correct ≈ 258/section  (Stuyvesant cutoff, 517 composite)
#   Easy path, ~25/57 correct ≈ 231/section  (Brooklyn Tech cutoff, 463 composite)
#   Both paths: 0/57 → 200,  57/57 → 400
#   Random guessing (14/57, 25% on 4-choice MC) → ~210 on easy path → ~420 composite
#   (well below any cutoff, as expected)
#
# These tables are approximations — the DOE does not publish conversion tables.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Legacy: manual score logging (pre-adaptive, 47 scored questions)
# ---------------------------------------------------------------------------

_LEGACY_SCALE = {
    0: 100, 1: 103, 2: 107, 3: 111, 4: 115, 5: 119, 6: 123, 7: 127, 8: 131, 9: 135,
    10: 139, 11: 143, 12: 147, 13: 151, 14: 155, 15: 159, 16: 163, 17: 167, 18: 171, 19: 175,
    20: 179, 21: 183, 22: 187, 23: 191, 24: 195, 25: 200, 26: 205, 27: 210, 28: 215, 29: 220,
    30: 225, 31: 230, 32: 237, 33: 244, 34: 251, 35: 258, 36: 265, 37: 272, 38: 279, 39: 286,
    40: 293, 41: 300, 42: 307, 43: 314, 44: 320, 45: 330, 46: 342, 47: 355,
}


def scale_score(raw: int) -> int:
    """Legacy: scaled section score for manually logged scores (0–47 correct)."""
    raw = max(0, min(raw, 47))
    return _LEGACY_SCALE[raw]


# ---------------------------------------------------------------------------
# Adaptive: 57 scored questions per section (routing + one module)
# ---------------------------------------------------------------------------

def _build_table(anchors: list[tuple[int, int]]) -> dict[int, int]:
    """Piecewise-linear interpolation over anchor points → full lookup dict."""
    table = {}
    for i in range(len(anchors) - 1):
        x0, y0 = anchors[i]
        x1, y1 = anchors[i + 1]
        for x in range(x0, x1):
            t = (x - x0) / (x1 - x0)
            table[x] = round(y0 + t * (y1 - y0))
    table[anchors[-1][0]] = anchors[-1][1]
    return table


# Easy-module path: conservative credit — easier questions
_EASY_ANCHORS = [
    (0, 200), (7, 204), (14, 210), (21, 222), (28, 238),
    (35, 260), (42, 290), (50, 340), (57, 400),
]

# Hard-module path: more generous credit — harder questions
_HARD_ANCHORS = [
    (0, 200), (7, 210), (14, 226), (21, 250), (28, 275),
    (35, 307), (42, 340), (50, 375), (57, 400),
]

_EASY_TABLE = _build_table(_EASY_ANCHORS)
_HARD_TABLE = _build_table(_HARD_ANCHORS)


def scale_score_adaptive(raw: int, module: str) -> int:
    """
    Scaled section score for adaptive tests.
    raw    — correct answers on routing + assigned module combined (0–57)
    module — 'easy' or 'hard'
    """
    raw = max(0, min(raw, 57))
    table = _HARD_TABLE if module == 'hard' else _EASY_TABLE
    return table[raw]


# ---------------------------------------------------------------------------
# School placement
# ---------------------------------------------------------------------------

def compute_placement(composite: int | None, cutoffs) -> list[dict]:
    """
    Return placement info for each school relative to current composite.
    """
    if composite is None:
        return []
    result = []
    for c in cutoffs:
        gap = composite - c.cutoff_score
        if gap >= 0:
            status, heat_bg = "above", "#1a7f3c"
        elif gap >= -30:
            status, heat_bg = "close", "#52796f"
        elif gap >= -60:
            status, heat_bg = "below", "#8a6700"
        elif gap >= -100:
            status, heat_bg = "below", "#b5540a"
        else:
            status, heat_bg = "below", "#a4161a"
        result.append({
            "school_short": c.school_short,
            "school_name": c.school_name,
            "cutoff": c.cutoff_score,
            "seats": c.approximate_seats,
            "gap": gap,
            "status": status,
            "heat_bg": heat_bg,
        })
    return result
