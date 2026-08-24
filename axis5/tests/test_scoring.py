"""
Scoring tests for AXIS-5.

All 40 checks from reference_scorer.py::_tests() are ported here,
plus Django-specific additions. The reference scorer is the oracle —
if this file and the reference scorer disagree, fix this file.
"""
import json
import os
from django.test import TestCase
from axis5.services.scoring import score_session, score_calibration, SCORING_VERSION


def _load_form():
    path = os.path.join(os.path.dirname(__file__), "../../axis5/docs/items.json")
    with open(os.path.abspath(path)) as f:
        return json.load(f)


def _cal(pairs):
    """pairs: [(answer, confidence), ...] in K1..K8 order"""
    return [
        {"id": f"K{i + 1}", "answer": a, "confidence": c}
        for i, (a, c) in enumerate(pairs)
    ]


PERFECT = {
    "calibration": _cal([
        (True, 95), (False, 98), (True, 92), (False, 98),
        (False, 90), (True, 95), (True, 90), (False, 92),
    ]),
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


class PerfectRunTests(TestCase):
    """Test 1 — a perfect run is Robust everywhere with no direction."""

    def setUp(self):
        self.form = _load_form()
        self.r = score_session(self.form, PERFECT)

    def test_all_dimensions_robust(self):
        for d in "UMCAE":
            with self.subTest(d=d):
                self.assertEqual(self.r["dimensions"][d]["band"], "Robust")

    def test_no_direction_anywhere(self):
        for d in "UMCAE":
            with self.subTest(d=d):
                self.assertIsNone(self.r["dimensions"][d]["direction"])

    def test_u_has_3_units(self):
        self.assertEqual(self.r["dimensions"]["U"]["total"], 3)

    def test_m_has_4_units(self):
        self.assertEqual(self.r["dimensions"]["M"]["total"], 4)


class OverconfidenceTests(TestCase):
    """Test 2 — high confidence, low accuracy."""

    def setUp(self):
        form = _load_form()
        over = dict(PERFECT)
        over["calibration"] = _cal([(True, 95)] * 8)
        self.r = score_session(form, over)

    def test_verdict(self):
        self.assertEqual(self.r["calibration"]["verdict"], "overconfident")

    def test_accuracy(self):
        self.assertAlmostEqual(self.r["calibration"]["accuracy"], 0.5)

    def test_gap(self):
        self.assertAlmostEqual(self.r["calibration"]["gap"], 0.45, places=6)

    def test_u_band_drops(self):
        self.assertEqual(self.r["dimensions"]["U"]["band"], "Aligned")

    def test_u_direction(self):
        self.assertEqual(self.r["dimensions"]["U"]["direction"], "+")


class SelectAllTests(TestCase):
    """Test 3 — selecting everything must not pass a select_all item."""

    def setUp(self):
        form = _load_form()
        greedy = dict(PERFECT)
        greedy["M-01"] = [1, 2, 3, 4, 5, 6, 7]
        self.r = score_session(form, greedy)

    def test_fails(self):
        self.assertFalse(self.r["items"]["M-01"]["correct"])

    def test_pole_plus(self):
        self.assertEqual(self.r["items"]["M-01"]["pole"], "+")


class C01DifferenceTests(TestCase):
    """Test 4 — C-01 is scored on the difference, not either answer alone."""

    def setUp(self):
        self.form = _load_form()

    def test_both_up_fails(self):
        both_up = dict(PERFECT)
        both_up["C-01"] = {"a": "up", "b": "rise"}
        r = score_session(self.form, both_up)
        self.assertFalse(r["items"]["C-01"]["correct"])
        self.assertEqual(r["items"]["C-01"]["pole"], "-")

    def test_both_none_fails(self):
        same_none = dict(PERFECT)
        same_none["C-01"] = {"a": "same", "b": "nochange"}
        r = score_session(self.form, same_none)
        self.assertFalse(r["items"]["C-01"]["correct"])
        self.assertEqual(r["items"]["C-01"]["pole"], "+")


class A02Tests(TestCase):
    """Tests 5 & 6 — A-02 big drop, and gating."""

    def setUp(self):
        self.form = _load_form()

    def test_big_drop_fails(self):
        anec = dict(PERFECT)
        anec["A-02"] = {"step1": 68, "step2": 50}
        r = score_session(self.form, anec)
        self.assertFalse(r["items"]["A-02"]["correct"])
        self.assertEqual(r["items"]["A-02"]["pole"], "-")

    def test_bad_step1_flagged_not_pole(self):
        bad1 = dict(PERFECT)
        bad1["A-02"] = {"step1": 34, "step2": 30}
        r = score_session(self.form, bad1)
        self.assertIn("arithmetic_issue", r["items"]["A-02"]["flags"])
        self.assertIsNone(r["items"]["A-02"]["pole"])


class E01Tests(TestCase):
    """Test 7 — E-01: under-updating vs base-rate neglect are different events."""

    def setUp(self):
        self.form = _load_form()

    def test_rigid_pole_minus(self):
        rigid = dict(PERFECT)
        rigid["E-01"] = {"step1": 12, "step2": 20}
        r = score_session(self.form, rigid)
        self.assertEqual(r["items"]["E-01"]["pole"], "-")

    def test_base_rate_neglect_flagged_no_e_pole(self):
        brn = dict(PERFECT)
        brn["E-01"] = {"step1": 12, "step2": 85}
        r = score_session(self.form, brn)
        self.assertIn("base_rate_neglect", r["items"]["E-01"]["flags"])
        self.assertIsNone(r["items"]["E-01"]["pole"])


class E03Tests(TestCase):
    """Test 8 — E-03: rejecting a trivial entailment flips the pole to +."""

    def setUp(self):
        form = _load_form()
        skep = dict(PERFECT)
        skep["E-03"] = [3]
        self.r = score_session(form, skep)

    def test_flagged(self):
        self.assertIn("indiscriminate_skepticism", self.r["items"]["E-03"]["flags"])

    def test_pole_plus(self):
        self.assertEqual(self.r["items"]["E-03"]["pole"], "+")


class E02Tests(TestCase):
    """Test 9 — E-02: flat allocation is false equivalence."""

    def setUp(self):
        self.form = _load_form()

    def test_flat_fails(self):
        flat = dict(PERFECT)
        flat["E-02"] = {"1": 25, "2": 25, "3": 25, "4": 25}
        r = score_session(self.form, flat)
        self.assertFalse(r["items"]["E-02"]["correct"])
        self.assertEqual(r["items"]["E-02"]["pole"], "-")

    def test_track_record_pole_plus(self):
        tech = dict(PERFECT)
        tech["E-02"] = {"1": 30, "2": 20, "3": 20, "4": 30}
        r = score_session(self.form, tech)
        self.assertEqual(r["items"]["E-02"]["pole"], "+")


class AllocateSumTests(TestCase):
    """Test 10 — allocation that does not sum to 100 is flagged."""

    def test_bad_sum_flagged(self):
        form = _load_form()
        bad = dict(PERFECT)
        bad["M-04"] = {"1": 5, "2": 75, "3": 5}
        r = score_session(form, bad)
        self.assertIn("allocation_does_not_sum", r["items"]["M-04"]["flags"])


class MixedPolesTests(TestCase):
    """Test 11 — mixed poles within a dimension produce no direction."""

    def setUp(self):
        form = _load_form()
        mixed = dict(PERFECT)
        mixed["A-02"] = {"step1": 68, "step2": 50}  # pole -
        mixed["A-03"] = "A"                           # pole +
        self.r = score_session(form, mixed)

    def test_no_direction(self):
        self.assertIsNone(self.r["dimensions"]["A"]["direction"])

    def test_band_emerging(self):
        self.assertEqual(self.r["dimensions"]["A"]["band"], "Emerging")


class SparseResponseTests(TestCase):
    """Test 12 — missing responses do not crash and count as incorrect."""

    def test_sparse_survives(self):
        form = _load_form()
        sparse = {"calibration": PERFECT["calibration"], "U-01": "A"}
        r = score_session(form, sparse)
        self.assertEqual(r["dimensions"]["M"]["band"], "Misaligned")


class UnscoredItemTests(TestCase):
    """Test 13 — E-04 is collected, never scored."""

    def test_e04_unscored(self):
        form = _load_form()
        r = score_session(form, PERFECT)
        self.assertFalse(r["items"]["E-04"]["scored"])


class ScoringVersionTests(TestCase):
    """Scoring version is recorded in the payload."""

    def test_version_in_payload(self):
        form = _load_form()
        r = score_session(form, PERFECT)
        self.assertEqual(r["scoring_version"], SCORING_VERSION)
        self.assertEqual(r["form_version"], form["form"]["form_version"])
