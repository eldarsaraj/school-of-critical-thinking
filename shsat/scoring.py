# Conservative ELA/Math scaling table (same for both sections).
# Only 47 of 57 questions are scored; use min(raw, 47) before looking up.
# Max composite ≈ 710. Real SHSAT max is 800 — intentionally conservative.

_SCALE = {
    0: 100, 1: 103, 2: 107, 3: 111, 4: 115, 5: 119, 6: 123, 7: 127, 8: 131, 9: 135,
    10: 139, 11: 143, 12: 147, 13: 151, 14: 155, 15: 159, 16: 163, 17: 167, 18: 171, 19: 175,
    20: 179, 21: 183, 22: 187, 23: 191, 24: 195, 25: 200, 26: 205, 27: 210, 28: 215, 29: 220,
    30: 225, 31: 230, 32: 237, 33: 244, 34: 251, 35: 258, 36: 265, 37: 272, 38: 279, 39: 286,
    40: 293, 41: 300, 42: 307, 43: 314, 44: 320, 45: 330, 46: 342, 47: 355,
}


def scale_score(raw: int) -> int:
    """Return scaled section score for a raw correct count (0–47)."""
    raw = max(0, min(raw, 47))
    return _SCALE[raw]


def compute_placement(composite: int | None, cutoffs) -> list[dict]:
    """
    Return a list of dicts with placement info for each school.
    composite — the student's composite score (or None).
    cutoffs   — QuerySet or iterable of CutoffScore objects.
    """
    if composite is None:
        return []
    result = []
    for c in cutoffs:
        gap = composite - c.cutoff_score
        if gap >= 0:
            status = "above"
        elif gap >= -30:
            status = "close"
        else:
            status = "below"
        if gap >= 0:
            heat_bg = "#1a7f3c"
        elif gap >= -30:
            heat_bg = "#52796f"
        elif gap >= -60:
            heat_bg = "#8a6700"
        elif gap >= -100:
            heat_bg = "#b5540a"
        else:
            heat_bg = "#a4161a"
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
