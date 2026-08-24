# AXIS-5 v1 — Implementation Spec

Django + PostgreSQL. Single-form assessment with accounts.
Companion files: `items.json` (all content and keys), `reference_scorer.py` (the scoring oracle).

---

## 1. Scope

**In:** account signup/login, one 26-response assessment, server-side scoring, a results page, email delivery of results, an admin view of item statistics.

**Out of scope for v1 — do not build:** adaptive item selection, IRT, percentiles or norms, multiple forms, pre/post comparison, team reporting, payment, PDF export, social sharing, i18n.

If a requirement isn't in this file, it isn't in v1.

---

## 2. Hard constraints

These are correctness requirements, not preferences. Violating any one invalidates the instrument.

1. **Scoring is server-side. Answer keys never reach the browser.** Serialize items to the client with keys, `target`, `correct`, `pole`, `derivation`, and `answer` fields stripped. Write a test that fetches the item payload as an anonymous user and asserts none of those keys appear anywhere in the response body.

2. **`A-02` and `E-01` are sequential. Step 2 must be hidden until step 1 is submitted, and step 1 must be locked once submitted.** Both items measure how an estimate *moves*. If both steps are visible at once, or step 1 can be edited after seeing step 2, the item measures nothing at all. Server must reject a step-2 submission that arrives without a stored step-1.

3. **Store raw responses forever, separately from scores.** `Result` is a cache. It must be fully reproducible from `Response` rows plus a scoring version. Provide a management command `rescore_all --scoring-version=N`.

4. **Version everything.** Every `Result` records `form_version` and `scoring_version`. Never mutate an item in place once it has responses — supersede it with a new row.

5. **Record milliseconds per item** (first interaction and total) plus a count of answer changes.

6. **`select_all` items must never display how many options are correct**, and must not cap selections. Selecting everything has to be possible and has to fail.

7. **Do not randomize item order in v1.** Fixed order keeps your first ~50 item statistics comparable. Randomization comes in v2 with a bigger bank.

---

## 3. Models

```
User                    Django default + email as username

Item                    item_id (unique)   dimension   format   tier
                        domain   tag   payload (JSONB)   scored (bool)
                        field_test (bool, default False)
                        form_version   active (bool)   position (int)

Form                    form_id   form_version   scoring_version   active

Session                 user (FK, nullable for anonymous)   form_version
                        started_at   completed_at   state
                        user_agent   ip_hash

Response                session (FK)   item (FK)   value (JSONB)
                        ms_first   ms_total   n_changes   created_at

Result                  session (OneToOne)   form_version   scoring_version
                        payload (JSONB)   computed_at
```

`Item.payload` holds the object from `items.json` verbatim. Do not normalize options into their own tables — the formats differ too much and you will be editing content constantly. JSONB plus a loader command is right here.

The calibration block is stored as **one Item** with `format="tf_confidence_block"` and its eight statements inside `payload`, submitted as one `Response` whose `value` is the array of eight answers. This keeps "the calibration block is one scored unit" true in the data model rather than only in the scoring code.

**Loader:** `python manage.py load_items items.json` — idempotent, upserts by `(item_id, form_version)`, refuses to overwrite an item that already has responses unless `--force`.

---

## 4. Scoring

`reference_scorer.py` is the specification. Port it to `assessment/services/scoring.py`, preserving function boundaries so the tests map across.

Summary of what it does:

- **Calibration block** → `gap = mean(confidence)/100 − accuracy`. Scored as one unit toward Uncertainty. `|gap| ≤ 0.15` is correct. `gap > 0.15` → `+` pole; `gap < −0.10` → `−` pole. The thresholds are asymmetric on purpose: mild overconfidence is near-universal, underconfidence is rare enough that a smaller gap means something.
- **Every other item** → correct/incorrect, plus a pole (`−` or `+`) when incorrect, read from the item's pole rules.
- **Per dimension** → count correct; map to a band. Uncertainty has 3 units, the rest have 4.

| Correct | Band (4 units) | | Correct | Band (3 units) |
|---|---|---|---|---|
| 0–1 | Misaligned | | 0 | Misaligned |
| 2 | Emerging | | 1 | Emerging |
| 3 | Aligned | | 2 | Aligned |
| 4 | Robust | | 3 | Robust |

- **Direction** → majority pole among that dimension's wrong answers. A tie, or no wrong answers, yields `null`, which the results page renders as "no clear lean in either direction." That's a real result, not a gap.

**Three rules that are easy to get wrong and are covered by tests:**

- `select_all` is correct only if *every* target is selected and *no* foil is. Partial credit does not exist here.
- `C-01` is scored on the difference between its two parts. Answering "up" to both is a failure; so is answering "no change" to both, in the opposite direction.
- `E-01` step 2 above 65 is **not** an epistemic-humility failure. It's base-rate neglect, which belongs to Uncertainty. Record the flag, assign no `E` pole.

---

## 5. Endpoints

```
GET   /assessment/start/            create session, redirect to first item
GET   /assessment/<session>/item/<n>/    render item n (keys stripped)
POST  /assessment/<session>/item/<n>/    save response, advance
POST  /assessment/<session>/item/<n>/step/  two_step only: save step 1, unlock step 2
POST  /assessment/<session>/complete/    score, store Result, redirect
GET   /results/<session>/           render Result
GET   /admin/item-stats/            staff only, see section 7
```

Resumable: a returning user with an incomplete session continues at their first unanswered item. Sessions expire after 7 days incomplete.

---

## 6. Front-end behaviour per format

| Format | Control | Validation |
|---|---|---|
| `tf_confidence_block` | 8 rows: True/False toggle + slider 50–100 | all 8 answered |
| `mc` | radio group | one selected |
| `mc_multi` | two radio groups on one page | both answered |
| `select_all` | checkboxes, no counter, no cap | at least one — or allow zero and score it |
| `scope_grid` | rows × 3 radio columns | every row answered |
| `allocate` | 3–4 number inputs + live running total | must sum to exactly 100; block submit otherwise |
| `two_step` | step 1 alone; on submit, lock it and reveal step 2 | step 1 locked before step 2 renders |
| `open_text` | textarea with word counter | 60–120 words, soft warning only |

Slider defaults: **start the confidence slider unset**, not at 75. A pre-filled midpoint is an anchor and will bias the single most important measurement in the test.

---

## 7. Admin item statistics

One staff-only page. For each item: N, percent correct, median seconds, and — for `mc` — the distribution of chosen options.

Sort by percent correct. This page is how you find broken items:

- **>90% correct** → not discriminating, cut or harden
- **<20% correct** → item broken *or your key is wrong*; check the derivation before blaming respondents
- **a wrong option chosen more than the right one** → ambiguous stem
- **median under 5 seconds** → too easy, or skimming

Also compute, per dimension, a **top-third vs bottom-third split**: rank respondents by that dimension's score, and for each item show the percent correct in the top third and the bottom third. An item where those two numbers are equal is not measuring what its neighbours measure. This is a poor man's item-total correlation and it catches most of what a real one would.

Exclude flagged sessions (see §8) from these statistics.

---

## 8. Response quality flags

Compute at completion, store on `Result`, do not block anyone:

- `rapid_responding` — more than 25% of items answered in under 5 seconds
- `straightlining` — every confidence slider within 5 points of each other
- `incomplete` — any item missing

Flagged sessions still get results. They're excluded from item statistics.

---

## 9. Acceptance tests

Port every test in `reference_scorer.py::_tests` (40 checks) into the Django test suite, plus:

- item payload served to the client contains no `correct`, `target`, `answer`, `pole`, `key`, or `derivation` field
- `A-02` and `E-01` reject a step-2 POST with no stored step-1
- `A-02` and `E-01` reject an edit to step 1 after step 2 has been served
- `allocate` rejects a submission summing to anything but 100
- `select_all` accepts a submission selecting every option, and scores it incorrect
- `rescore_all` reproduces stored `Result` payloads byte-for-byte at the same scoring version
- an anonymous user can complete a session; results are claimable on later signup

---

## 10. Field-test hook

`Item.field_test = True` means: serve it, store the response, **exclude it from scoring entirely**.

Rules: serve 2–3 per session, drawn at random from active field-test items; never in the first or last position; users are never told which. Add the column and the exclusion logic now even with zero such items in the bank — it costs ten lines and it's how the question bank grows without ever running a separate study.

---

## 11. Results page

Content and copy are specified in the build document (§5). Implementation notes only:

- Render from the stored `Result` payload. Never recompute at view time.
- The calibration panel comes first: confidence, accuracy, and the gap, with a small chart plotting the respondent's point against the diagonal where the two would be equal.
- Five horizontal bars for the bands. **Not a radar chart** — area scales as the square of the radius, so radar exaggerates small differences, and the shape depends on arbitrary axis ordering. Use the pentagon lower down as a shareable image only.
- Every dimension shows band + direction sentence. Direction `null` renders as "no clear lean in either direction here."
- The honest-limits line appears on the page, not in a footer: *"This is an indication, not a measurement. Four questions per dimension can show you roughly where you stand and which direction you lean. They can't tell you by how much."*
- No numbers, no percentages, no percentiles, no comparison to other users. There are no norms. Anything numeric implies a precision that 26 responses cannot support.
