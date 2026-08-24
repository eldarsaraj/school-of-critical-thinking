# Claude Code prompts

Put `SPEC.md`, `items.json` and `reference_scorer.py` in the repo root first. Then work through these in order — one stage per session, review between them.

Don't paste the build document. It's a design rationale; Claude Code needs constraints and data, and re-deriving data structures from prose tables is where transcription errors in your answer keys come from.

---

## Stage 0 — project setup

```
Read SPEC.md.

Set up a Django 5 project called `axis5` with a PostgreSQL backend and one
app called `assessment`. Use uv for dependency management. Add pytest and
pytest-django.

Create the models from SPEC.md section 3 exactly as specified: User (Django
default, email as username), Item, Form, Session, Response, Result. Item.payload
and Response.value are JSONB.

Then write `python manage.py load_items <path>`: idempotent, upserts by
(item_id, form_version), refuses to overwrite an item that already has responses
unless --force. Load items.json with it.

The calibration block loads as a SINGLE Item with format "tf_confidence_block"
and its eight statements inside payload. It is one scored unit, and the data
model should say so.

Stop there. Do not build views yet.
```

**Check before moving on:** `load_items items.json` runs twice with no duplicates, and the DB has 19 Item rows (18 main + 1 calibration block).

---

## Stage 1 — scoring

```
Read SPEC.md section 4 and reference_scorer.py.

Port reference_scorer.py to assessment/services/scoring.py. Keep the same
function boundaries (score_calibration, the per-format scorers, score_session)
so tests map across one to one.

reference_scorer.py is the oracle. Where the spec prose and the code disagree,
the code is right.

Then port all 40 checks in reference_scorer.py::_tests into pytest tests in
assessment/tests/test_scoring.py. They must all pass.

Add `python manage.py rescore_all --scoring-version=N`.

No views yet.
```

**Check:** `pytest assessment/tests/test_scoring.py` — 40 passing. Then run `python reference_scorer.py` and confirm both agree.

Doing scoring before any UI is deliberate. It's the part where correctness matters and the part that's cheapest to verify in isolation.

---

## Stage 2 — assessment flow

```
Read SPEC.md sections 2, 5 and 6.

Build the assessment flow: the endpoints in section 5, one item per page,
resumable, anonymous sessions allowed.

Four hard requirements from section 2, each needing a test:

1. Answer keys must never reach the browser. Write a serializer that strips
   `correct`, `target`, `answer`, `pole`, `key`, and `derivation` from item
   payloads, and a test that fetches an item as an anonymous user and asserts
   none of those strings appear in the response body.

2. A-02 and E-01 are sequential. Step 2 must not be rendered or reachable until
   step 1 is submitted, and step 1 must be locked once submitted. Reject a
   step-2 POST with no stored step-1. Reject an edit to step 1 after step 2 has
   been served. These two items measure how an estimate MOVES; if both steps are
   visible at once the items measure nothing.

3. Record ms_first, ms_total and n_changes for every response.

4. Item order is fixed, from Item.position. Do not randomize.

Front-end: plain Django templates and vanilla JS. No React, no build step.
Section 6 has the control and validation rules per format. Note especially:
select_all shows no counter and no cap; the confidence slider starts UNSET, not
at a midpoint.
```

**Check:** take the whole thing yourself end to end. Watch for the two-step items specifically — that's where a naive build puts both steps on one page and silently breaks the measurement.

---

## Stage 3 — results

```
Read SPEC.md section 11, and section 5 of the build document for the exact copy.

Build the results page, rendered from the stored Result payload, never
recomputed at view time.

Order: calibration panel, five band bars, five direction sentences, the
strongest-pattern paragraph, routing links, honest-limits line.

The calibration panel shows confidence, accuracy, and the gap, plus a small
chart: the respondent's point plotted against the diagonal where confidence
equals accuracy. Inline SVG, no chart library.

Five horizontal bars for the bands, sorted by band. NOT a radar chart — radar
exaggerates small differences because area scales as the square of the radius,
and the shape depends on arbitrary axis ordering. The pentagon appears lower on
the page as a shareable image only.

Direction null renders as "no clear lean in either direction here."

No numbers, no percentages, no percentiles, no comparison to other users. There
are no norms yet and anything numeric would imply precision that 26 responses
cannot support.
```

**Check:** show it to three people who haven't seen the test. If they can't say what their weakest dimension is and which way they lean, the page has failed regardless of how it looks.

---

## Stage 4 — accounts, email, admin

```
Read SPEC.md sections 7, 8 and 10.

1. Accounts: signup, login, password reset. An anonymous session's results are
   claimable when the user signs up afterwards — carry the session id through.

2. Email the results link on completion. Plain text is fine.

3. Response quality flags per section 8, computed at completion, stored on
   Result. Never block anyone; flagged sessions still get full results.

4. Staff-only item statistics page per section 7: N, percent correct, median
   seconds, option distribution for mc items, and the top-third vs bottom-third
   split per dimension. Exclude flagged sessions. Sort by percent correct.

5. The field-test hook per section 10: Item.field_test = True means serve it,
   store the response, exclude it from scoring completely. Serve 2-3 per
   session at random, never first or last. Implement it now even though the
   bank has none yet.
```

**Check:** the item-statistics page is the one you'll live in after the presentation. Make sure it's usable before you need it, not after.

---

## Stage 5 — before launch

```
Read SPEC.md section 9. Write any acceptance tests from that list that don't
exist yet, and make them pass.

Then: run through the full flow as an anonymous user on a phone, complete it,
sign up, and confirm the results carry over.
```

---

## Working notes

**When Claude Code wants to change an answer key**, don't let it. If a key looks wrong, check the `derivation` field on that item — every key has one. If the derivation is genuinely wrong, fix `items.json` and reload; never patch it in the scoring code, or the data and the logic drift apart and you'll never find out which is right.

**When it suggests a JS framework, a chart library, or a component system**, decline. Everything here is form controls and one small SVG.

**Item content lives in `items.json`, never in templates or code.** You'll be editing questions constantly after the first thirty responses. Anything that hardcodes a stem will fight you every time.

**Keep `reference_scorer.py` in the repo permanently.** When you change scoring later — and you will, once you see real responses — change it there first, watch its tests fail, fix them, then port. It's the only thing standing between you and a scoring rule that quietly changed meaning between versions.
