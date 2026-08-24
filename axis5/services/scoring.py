"""
AXIS-5 scoring service.

Ported from axis5/docs/Reference scorer.py (the oracle).
Where this file and the spec prose disagree, the reference scorer is right.

The function boundaries are preserved 1:1 so tests map across directly.
"""

SCORING_VERSION = 1

BANDS_4 = ["Misaligned", "Misaligned", "Emerging", "Aligned", "Robust"]
BANDS_3 = ["Misaligned", "Emerging", "Aligned", "Robust"]


# ---------------------------------------------------------------- calibration


def score_calibration(block, responses):
    """
    responses: [{"id": "K1", "answer": True, "confidence": 80}, ...]

    Returns accuracy, mean confidence, and the gap between them.
    The gap IS the result; everything else on the calibration panel is derived from it.
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
    """response: {"a": "up", "b": "nochange"} — all parts must be correct."""
    all_correct = True
    for part in item["parts"]:
        given = response.get(part["id"])
        opt = next((o for o in part["options"] if o["id"] == given), None)
        if opt is None or not opt.get("correct"):
            all_correct = False
    if all_correct:
        return True, None, []
    for combo in item.get("combination_poles", []):
        if all(response.get(k) == v for k, v in combo["answers"].items()):
            return False, combo["pole"], []
    return False, item.get("default_pole"), []


def _score_select_all(item, response):
    """
    response: list of selected option ids.
    Correct only if every target is selected and no foil is.
    Selecting everything must never be a winning move.
    """
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
    """response: {"1": "holds", "2": "breaks", ...} — all rows must be right."""
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
    v = alloc.get(str(cond["option"]), alloc.get(cond.get("option", ""), 0))
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
    raise ValueError(f"unknown allocate op: {op}")


def _score_allocate(item, response):
    """response: {"1": 5, "2": 75, "3": 20} — must sum to the stated total."""
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
    """
    form:      the parsed items.json dict
    responses: {"calibration": [...], "U-01": "A", "M-01": [1,2,4,5], ...}

    Returns the full scoring payload, suitable for storing in Result.payload.
    """
    per_item = {}
    flags = []
    dim_correct = {d: 0 for d in form["form"]["dimensions"]}
    dim_total = {d: 0 for d in form["form"]["dimensions"]}
    dim_poles = {d: [] for d in form["form"]["dimensions"]}

    # Calibration block — counts as one unit toward U
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
