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
# Calibration targets (2026 admissions cutoffs):
#   Stuyvesant:    561 composite → 280.5/section avg
#   Bronx Science: 525 composite → 262.5/section avg
#   Brooklyn Tech: 506 composite → 253.0/section avg
#   Brooklyn Latin:495 composite → 247.5/section avg
#
#   Hard path: ~42/57 (74%) correct ≈ 281/section (Stuyvesant territory)
#   Hard path: ~35/57 (61%) correct ≈ 264/section (Bronx Science territory)
#   Easy path: ~40/57 (70%) correct ≈ 253/section (Brooklyn Tech territory)
#   Easy path: ~35/57 (61%) correct ≈ 248/section (Brooklyn Latin territory)
#
#   Ceiling: 57/57 → 350/section → 700 composite max
#     The all-time SHSAT record is 689; 800 is statistically impossible.
#     Average test-taker scores ~400 composite (200/section) = our floor.
#
#   Random guessing (14/57, 25% on 4-choice MC):
#     → ~208/section easy, ~216/section hard → ~416-432 composite
#     (well below the 495 Brooklyn Latin floor, as expected)
#
#   Intentionally conservative — students should not overestimate readiness.
#   These are piecewise-linear approximations; the DOE does not publish tables.
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


# Easy-module path: conservative — easier questions earn less per correct answer
# ~40/57 (70%) needed for Brooklyn Tech territory (~253/section)
# ~35/57 (61%) needed for Brooklyn Latin territory (~248/section)
# Ceiling: 57/57 → 350/section (composite 700) — all-time record is 689
_EASY_ANCHORS = [
    (0, 200), (7, 203), (14, 208), (21, 216), (28, 230),
    (35, 248), (40, 253), (46, 285), (50, 310), (57, 350),
]

# Hard-module path: more generous — harder questions earn more per correct answer
# ~42/57 (74%) needed for Stuyvesant territory (~281/section)
# ~35/57 (61%) needed for Bronx Science territory (~264/section)
# Ceiling: 57/57 → 350/section (composite 700) — all-time record is 689
_HARD_ANCHORS = [
    (0, 200), (7, 207), (14, 216), (21, 229), (28, 249),
    (35, 264), (42, 281), (50, 320), (57, 350),
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
