"""
AXIS-5 v1 reference scorer.

This is the specification of the scoring rules, written as runnable code.
It is deliberately dependency-free and framework-free.

Port it into Django (services/scoring.py) and keep this file as the test oracle:
if the Django implementation and this file ever disagree, this file is right.

Run:  python reference_scorer.py        -> runs the self-tests
"""

import json
import os

SCORING_VERSION = 1

# Bands are indexed by number of units answered correctly.
BANDS_4 = ["Misaligned", "Misaligned", "Emerging", "Aligned", "Robust"]
BANDS_3 = ["Misaligned", "Emerging", "Aligned", "Robust"]


def load_form(path=None):
    path = path or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "items.json"
    )
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------- calibration


def score_calibration(block, responses):
    """responses: [{"id": "K1", "answer": True, "confidence": 80}, ...]

    Returns accuracy, mean confidence, and the gap between them. The gap IS the
    result; everything else on the calibration panel is derived from it.
    """
    by_id = {r["id"]: r for r in responses}
    n = len(block["items"])
    correct = 0
    confs = []
    for item in block["items"]:
        r = by_id.get(item["id"])
        if r is None:
            continue
        if bool(r["answer"]) == bool(item["answer"]):
            correct += 1
        confs.append(float(r["confidence"]))

    if not confs:
        return None

    accuracy = correct / n
    avg_conf = (sum(confs) / len(confs)) / 100.0
    gap = avg_conf - accuracy

    s = block["scoring"]
    unit_correct = abs(gap) <= s["unit_correct_if_abs_gap_lte"]

    if gap > s["overconfident_if_gap_gt"]:
        verdict, pole = "overconfident", s["pole_overconfident"]
    elif gap < s["underconfident_if_gap_lt"]:
        verdict, pole = "underconfident", s["pole_underconfident"]
    else:
        verdict, pole = "calibrated", None

    return {
        "n_items": n,
        "n_correct": correct,
        "accuracy": round(accuracy, 4),
        "avg_confidence": round(avg_conf, 4),
        "gap": round(gap, 4),
        "verdict": verdict,
        "unit_correct": unit_correct,
        "pole": None if unit_correct else pole,
    }


# --------------------------------------------------------------- item formats


def _score_mc(item, response):
    chosen = next((o for o in item["options"] if o["id"] == response), None)
    if chosen is None:
        return False, None, ["missing_response"]
    if chosen.get("correct"):
        return True, None, []
    return False, chosen.get("pole"), []


def _score_mc_multi(item, response):
    """response: {"a": "up", "b": "nochange"} - all parts must be correct."""
    flags = []
    all_correct = True
    for part in item["parts"]:
        given = response.get(part["id"])
        opt = next((o for o in part["options"] if o["id"] == given), None)
        if opt is None or not opt.get("correct"):
            all_correct = False
    if all_correct:
        return True, None, flags
    for combo in item.get("combination_poles", []):
        if all(response.get(k) == v for k, v in combo["answers"].items()):
            return False, combo["pole"], flags
    return False, item.get("default_pole"), flags


def _score_select_all(item, response):
    """response: list of selected option ids. Correct only if every target is
    selected and no foil is. Selecting everything must never be a winning move."""
    selected = set(response or [])
    targets = {o["id"] for o in item["options"] if o.get("target")}
    foils = {o["id"] for o in item["options"] if not o.get("target")}
    trivial = {o["id"] for o in item["options"] if o.get("trivial")}

    missed = targets - selected
    false_alarms = selected & foils
    correct = not missed and not false_alarms

    flags = []
    pole = None
    if not correct:
        if false_alarms and not missed:
            pole = item["poles"]["over_selection"]
        elif missed and not false_alarms:
            pole = item["poles"]["under_selection"]
        else:
            pole = item["poles"]["under_selection"]

    # E-03: rejecting a trivially-entailed target is a distinct diagnostic event
    for rule in item.get("special_rules", []):
        if rule.get("if_any_trivial_target_rejected") and (trivial - selected):
            flags.append(rule["flag"])
            if rule.get("overrides_pole"):
                pole = rule["pole"]

    return correct, pole, flags


def _score_scope_grid(item, response):
    """response: {"1": "holds", "2": "breaks", ...} - all rows must be right."""
    wrong_poles = []
    correct = True
    for row in item["rows"]:
        given = response.get(str(row["id"]), response.get(row["id"]))
        if given != row["answer"]:
            correct = False
            wp = row.get("wrong_poles", {})
            if given in wp:
                wrong_poles.append(wp[given])
    if correct:
        return True, None, []
    pole = _majority(wrong_poles)
    return False, pole, []


def _check_allocate_cond(cond, alloc):
    op = cond["op"]
    if op == "none_zero":
        return all(v > 0 for v in alloc.values())
    if op == "all_equal":
        return len(set(alloc.values())) == 1
    v = alloc.get(str(cond["option"]), alloc.get(cond["option"], 0))
    if op == "lte":
        return v <= cond["value"]
    if op == "gte":
        return v >= cond["value"]
    if op == "eq":
        return v == cond["value"]
    if op == "between":
        lo, hi = cond["value"]
        return lo <= v <= hi
    if op == "max":
        return v == max(alloc.values()) and list(alloc.values()).count(v) == 1
    raise ValueError("unknown allocate op: %s" % op)


def _score_allocate(item, response):
    """response: {"1": 5, "2": 75, "3": 20} - must sum to the stated total."""
    alloc = {str(k): float(v) for k, v in (response or {}).items()}
    flags = []
    total = item.get("total", 100)
    if abs(sum(alloc.values()) - total) > 0.51:
        flags.append("allocation_does_not_sum")
        return False, item.get("default_pole"), flags

    correct = all(_check_allocate_cond(c, alloc) for c in item["key"])
    if correct:
        return True, None, flags
    for rule in item.get("pole_rules", []):
        if _check_allocate_cond(rule["when"], alloc):
            return False, rule["pole"], flags
    return False, item.get("default_pole"), flags


def _score_two_step(item, response):
    """response: {"step1": 68, "step2": 67}"""
    flags = []
    s1 = response.get("step1")
    s2 = response.get("step2")
    if s1 is None or s2 is None:
        return False, None, ["missing_response"]
    s1, s2 = float(s1), float(s2)

    gate = item.get("gating")
    if gate:
        lo, hi = gate["score_only_if_step1_between"]
        if not (lo <= s1 <= hi):
            flags.append(gate["else_flag"])
            return False, None, flags

    k1, k2 = item["step1"]["key"], item["step2"]["key"]
    ok1 = k1["min"] <= s1 <= k1["max"]

    if k2.get("relative_to") == "step1":
        ok2 = abs(s2 - s1) <= k2["max_abs_change"]
    else:
        ok2 = k2["min"] <= s2 <= k2["max"]

    correct = ok1 and ok2
    if correct:
        return True, None, flags

    for rule in item.get("pole_rules", []):
        expr, val = rule["expr"], rule.get("value")
        hit = (
            (expr == "drop_gt" and s2 < s1 - val)
            or (expr == "increase" and s2 > s1)
            or (expr == "step2_lt" and s2 < val)
            or (expr == "step2_gt" and s2 > val)
        )
        if hit:
            if rule.get("flag"):
                flags.append(rule["flag"])
            return False, rule.get("pole"), flags

    return False, None, flags


SCORERS = {
    "mc": _score_mc,
    "mc_multi": _score_mc_multi,
    "select_all": _score_select_all,
    "scope_grid": _score_scope_grid,
    "allocate": _score_allocate,
    "two_step": _score_two_step,
}


def _majority(poles):
    poles = [p for p in poles if p]
    if not poles:
        return None
    minus, plus = poles.count("-"), poles.count("+")
    if minus > plus:
        return "-"
    if plus > minus:
        return "+"
    return None  # a genuine tie is reported as "no clear direction"


# ------------------------------------------------------------------- assembly


def score_session(form, responses):
    """responses: {"calibration": [...], "U-01": "A", "M-01": [1,2,4,5], ...}"""
    per_item = {}
    flags = []
    dim_correct = {d: 0 for d in form["form"]["dimensions"]}
    dim_total = {d: 0 for d in form["form"]["dimensions"]}
    dim_poles = {d: [] for d in form["form"]["dimensions"]}

    cal = score_calibration(form["calibration"], responses.get("calibration", []))
    if cal:
        d = form["calibration"]["dimension"]
        dim_total[d] += 1
        if cal["unit_correct"]:
            dim_correct[d] += 1
        elif cal["pole"]:
            dim_poles[d].append(cal["pole"])

    for item in form["items"]:
        if item.get("scored") is False:
            per_item[item["id"]] = {"scored": False}
            continue
        d = item["dimension"]
        dim_total[d] += 1
        resp = responses.get(item["id"])
        if resp is None:
            per_item[item["id"]] = {
                "correct": False,
                "pole": None,
                "flags": ["missing_response"],
            }
            continue
        correct, pole, item_flags = SCORERS[item["format"]](item, resp)
        per_item[item["id"]] = {"correct": correct, "pole": pole, "flags": item_flags}
        if correct:
            dim_correct[d] += 1
        elif pole:
            dim_poles[d].append(pole)
        for f in item_flags:
            flags.append({"item": item["id"], "flag": f})

    dimensions = {}
    for d in form["form"]["dimensions"]:
        n, k = dim_total[d], dim_correct[d]
        table = BANDS_3 if n == 3 else BANDS_4
        band = table[k] if k < len(table) else table[-1]
        pole = _majority(dim_poles[d])
        dimensions[d] = {
            "name": form["form"]["dimensions"][d],
            "correct": k,
            "total": n,
            "band": band,
            "direction": pole,
            "direction_label": (
                form["form"]["poles"][d]["minus"]
                if pole == "-"
                else form["form"]["poles"][d]["plus"] if pole == "+" else None
            ),
        }

    return {
        "scoring_version": SCORING_VERSION,
        "form_version": form["form"]["form_version"],
        "calibration": cal,
        "dimensions": dimensions,
        "items": per_item,
        "flags": flags,
    }


# ----------------------------------------------------------------- self-tests


def _cal(pairs):
    """pairs: [(answer, confidence), ...] in K1..K8 order"""
    return [
        {"id": "K%d" % (i + 1), "answer": a, "confidence": c}
        for i, (a, c) in enumerate(pairs)
    ]


PERFECT = {
    # all eight correct, confidence high enough to match: gap approx -0.05
    "calibration": _cal(
        [
            (True, 95),
            (False, 98),
            (True, 92),
            (False, 98),
            (False, 90),
            (True, 95),
            (True, 90),
            (False, 92),
        ]
    ),
    "U-01": "A",
    "U-02": "B",
    "M-01": [1, 2, 4, 5],
    "M-02": {"1": "holds", "2": "breaks", "3": "cant_tell", "4": "breaks"},
    "M-03": [2, 4, 6],
    "M-04": {"1": 5, "2": 75, "3": 20},
    "C-01": {"a": "up", "b": "nochange"},
    "C-02": [1, 3, 4, 6],
    "C-03": "C",
    "C-04": {"1": "no", "2": "yes", "3": "no", "4": "unaffected"},
    "A-01": "B",
    "A-02": {"step1": 68, "step2": 68},
    "A-03": "B",
    "A-04": {"1": "within", "2": "within", "3": "outside", "4": "cant_tell"},
    "E-01": {"step1": 12, "step2": 44},
    "E-02": {"1": 45, "2": 25, "3": 25, "4": 5},
    "E-03": [1, 3, 6],
}


def _tests():
    form = load_form()
    ok = 0
    fail = []

    def check(label, cond):
        nonlocal ok
        if cond:
            ok += 1
        else:
            fail.append(label)

    # 1. A perfect run is Robust everywhere with no direction.
    r = score_session(form, PERFECT)
    for d in "UMCAE":
        check("perfect %s band" % d, r["dimensions"][d]["band"] == "Robust")
        check("perfect %s no direction" % d, r["dimensions"][d]["direction"] is None)
    check("U has 3 units", r["dimensions"]["U"]["total"] == 3)
    check("M has 4 units", r["dimensions"]["M"]["total"] == 4)

    # 2. Overconfidence: high confidence, low accuracy.
    over = dict(PERFECT)
    over["calibration"] = _cal(
        [
            (True, 95),
            (True, 95),
            (True, 95),
            (True, 95),
            (True, 95),
            (True, 95),
            (True, 95),
            (True, 95),
        ]
    )
    r = score_session(form, over)
    check("overconfident verdict", r["calibration"]["verdict"] == "overconfident")
    check("overconfident accuracy .5", r["calibration"]["accuracy"] == 0.5)
    check("overconfident gap .45", abs(r["calibration"]["gap"] - 0.45) < 1e-6)
    check("overconfident U drops", r["dimensions"]["U"]["band"] == "Aligned")
    check("overconfident U direction", r["dimensions"]["U"]["direction"] == "+")

    # 3. Selecting everything must not pass a select_all item.
    greedy = dict(PERFECT)
    greedy["M-01"] = [1, 2, 3, 4, 5, 6, 7]
    r = score_session(form, greedy)
    check("greedy select_all fails", r["items"]["M-01"]["correct"] is False)
    check("greedy select_all pole +", r["items"]["M-01"]["pole"] == "+")

    # 4. C-01 is scored on the DIFFERENCE, not either answer alone.
    same_up = dict(PERFECT)
    same_up["C-01"] = {"a": "up", "b": "rise"}
    r = score_session(form, same_up)
    check("C-01 both-up fails", r["items"]["C-01"]["correct"] is False)
    check("C-01 both-up pole -", r["items"]["C-01"]["pole"] == "-")

    same_none = dict(PERFECT)
    same_none["C-01"] = {"a": "same", "b": "nochange"}
    r = score_session(form, same_none)
    check("C-01 both-none fails", r["items"]["C-01"]["correct"] is False)
    check("C-01 both-none pole +", r["items"]["C-01"]["pole"] == "+")

    # 5. A-02: a big drop after one anecdote is the - pole.
    anec = dict(PERFECT)
    anec["A-02"] = {"step1": 68, "step2": 50}
    r = score_session(form, anec)
    check("A-02 big drop fails", r["items"]["A-02"]["correct"] is False)
    check("A-02 big drop pole -", r["items"]["A-02"]["pole"] == "-")

    # 6. A-02 gating: bad step1 arithmetic is flagged, not scored as a pole.
    bad1 = dict(PERFECT)
    bad1["A-02"] = {"step1": 34, "step2": 30}
    r = score_session(form, bad1)
    check("A-02 gate flags", "arithmetic_issue" in r["items"]["A-02"]["flags"])
    check("A-02 gate no pole", r["items"]["A-02"]["pole"] is None)

    # 7. E-01: under-updating vs base-rate neglect are different events.
    rigid = dict(PERFECT)
    rigid["E-01"] = {"step1": 12, "step2": 20}
    r = score_session(form, rigid)
    check("E-01 rigid pole -", r["items"]["E-01"]["pole"] == "-")

    brn = dict(PERFECT)
    brn["E-01"] = {"step1": 12, "step2": 85}
    r = score_session(form, brn)
    check("E-01 brn flagged", "base_rate_neglect" in r["items"]["E-01"]["flags"])
    check("E-01 brn no E pole", r["items"]["E-01"]["pole"] is None)

    # 8. E-03: rejecting a trivial entailment flips the pole to +.
    skep = dict(PERFECT)
    skep["E-03"] = [3]
    r = score_session(form, skep)
    check(
        "E-03 skeptic flagged",
        "indiscriminate_skepticism" in r["items"]["E-03"]["flags"],
    )
    check("E-03 skeptic pole +", r["items"]["E-03"]["pole"] == "+")

    # 9. E-02: a flat allocation is false equivalence, not even-handedness.
    flat = dict(PERFECT)
    flat["E-02"] = {"1": 25, "2": 25, "3": 25, "4": 25}
    r = score_session(form, flat)
    check("E-02 flat fails", r["items"]["E-02"]["correct"] is False)
    check("E-02 flat pole -", r["items"]["E-02"]["pole"] == "-")

    tech = dict(PERFECT)
    tech["E-02"] = {"1": 30, "2": 20, "3": 20, "4": 30}
    r = score_session(form, tech)
    check("E-02 track-record pole +", r["items"]["E-02"]["pole"] == "+")

    # 10. An allocation that does not sum to 100 is flagged.
    bad = dict(PERFECT)
    bad["M-04"] = {"1": 5, "2": 75, "3": 5}
    r = score_session(form, bad)
    check(
        "allocate sum flagged", "allocation_does_not_sum" in r["items"]["M-04"]["flags"]
    )

    # 11. Mixed poles within a dimension produce no direction.
    mixed = dict(PERFECT)
    mixed["A-02"] = {"step1": 68, "step2": 50}  # -
    mixed["A-03"] = "A"  # +
    r = score_session(form, mixed)
    check("mixed poles -> no direction", r["dimensions"]["A"]["direction"] is None)
    check("mixed poles band Emerging", r["dimensions"]["A"]["band"] == "Emerging")

    # 12. Missing responses do not crash and count as incorrect.
    sparse = {"calibration": PERFECT["calibration"], "U-01": "A"}
    r = score_session(form, sparse)
    check("sparse survives", r["dimensions"]["M"]["band"] == "Misaligned")

    # 13. E-04 is collected, never scored.
    check(
        "E-04 unscored",
        score_session(form, PERFECT)["items"]["E-04"]["scored"] is False,
    )

    print("passed %d checks" % ok)
    if fail:
        print("FAILED:")
        for f in fail:
            print("  -", f)
        return False
    return True


if __name__ == "__main__":
    import sys

    sys.exit(0 if _tests() else 1)
