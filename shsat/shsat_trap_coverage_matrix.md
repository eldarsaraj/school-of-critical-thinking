# SHSAT Practice Test — Trap Coverage Matrix

A planning reference for rotating cognitive-trap types and skills across multiple practice tests, derived from the [SHSAT Sample Test Design Checklist](shsat_test_design_checklist.md) and applied to Test 1 (`test_01_v5.yaml`) as the baseline.

## How to use this document

1. **For each new test you build**, copy the "Test 1 coverage" column to a new column ("Test 2 coverage", etc.) and mark which trap types you've included.
2. **The goal is not for every test to cover every trap type** — the goal is for the *set* of practice tests (Tests 1–4 or 1–6) to expose students to every trap at least once, with rotation so they can't pattern-match on a single test.
3. **Priority targets for Test 2** are listed at the bottom of each section. These are the traps that are absent or thin in v5 and should appear in your next test.

---

## Section 1 — Test structure invariants

These are constraints every test in the series should satisfy, not things to rotate.

| Constraint | Target | v5 status |
|---|---|---|
| ELA total questions | 57 | 85 (29 routing + 28 easy + 28 hard) — adaptive design intentionally exceeds the static 57 |
| Math total questions | 57 | 85 (29 routing + 28 easy + 28 hard) — same |
| Math grid-in count per module | 5 | ✓ routing=3 + easy=5 + hard=5 |
| Routing threshold | 0.6 | ✓ |
| Difficulty curve (easy → medium → hard) | Gradual rise within module | ✓ |
| No single skill > 30% of any module | True | ✓ for all six modules |
| Passage length 500–700 words | Within range | ✓ all four easy-module passages (571–606 words) |

---

## Section 2 — ELA Reading Comprehension Trap Types

The checklist names 13 named trap types for reading-comp distractors. v5 maps these to its own distractor labels; the table shows which are present and where.

| # | Checklist trap type | v5 internal label(s) | Test 1 (v5) | Test 2 | Test 3 | Test 4 | Notes |
|---|---|---|:---:|:---:|:---:|:---:|---|
| 1 | Overgeneralization | `too_broad` | ✓ (3 instances) | | | | Present but mostly in routing/hard. Add to easy. |
| 2 | Extreme Language Trap | `extreme_language` | ✓ (8 instances) | | | | Well covered. Strong "all/never/always" trigger words. |
| 3 | True-but-Irrelevant Trap | `true_but_irrelevant` | ⚠ (1 instance, Q21 easy) | | | | **Thin.** Add 2–3 per test going forward. |
| 4 | Partial Correctness Trap | — | ✗ MISSING | | | | **Highest priority for Test 2.** No internal label exists yet; create `partial_correctness`. |
| 5 | Surface Match Trap | `surface_match` | ✓ (3 instances, easy Q15, Q18) | | | | Decent coverage; rotate to inference/rhetoric questions in Test 2. |
| 6 | Opposite Meaning Trap | `opposite` | ✓ (35 instances) | | | | Heavily used; arguably overused. Reduce slightly in Test 2. |
| 7 | Scope Shift Trap | `distortion` (approximate) | ⚠ Partial — `distortion` is close but not identical | | | | **Create a dedicated `scope_shift` label.** Scope shift is specifically "specific→general" or "local→global." |
| 8 | Emotional Salience Trap | — | ✗ MISSING | | | | **Priority for Test 2 narrative passages.** Highly emotional wrong answers that attract weak readers. |
| 9 | Causal Confusion Trap | `causal_confusion` | ⚠ (1 instance, easy Q21) | | | | Add 2 more per test. |
| 10 | Inference Leap Trap | `inference_leap` | ⚠ (1 instance, easy Q12) | | | | Add 2 more per test. |
| 11 | Pronoun Reference Trap | — | ✗ MISSING | | | | **Priority for Test 2.** Requires passages with multiple plausible referents. |
| 12 | Chronology Trap | — | ✗ MISSING | | | | **Priority for Test 2.** Especially natural in narrative or historical passages. |
| 13 | Tone Misidentification Trap | — | ✗ MISSING | | | | **Priority for Test 2.** Requires passages with clear authorial stance (skeptical, sarcastic, etc.). |

### Internal-label cleanup tasks (one-time)

Before building Test 2, normalize these labels so the rotation is trackable:

- Add new labels to the taxonomy: `partial_correctness`, `scope_shift`, `emotional_salience`, `pronoun_reference`, `chronology`, `tone_misidentification`.
- Map existing usage: most current `distortion` instances are scope shifts and could be retagged.
- Reduce `unsupported` usage. It's a catch-all that signals weak distractor engineering; aim for ≤ 20% of distractors per module to be `unsupported`.

### Priority targets for Test 2 ELA (RC)

1. **Partial Correctness** — at least 2 instances. Best home: questions about author intent or main idea, where one part of the answer matches the passage and another doesn't.
2. **Pronoun Reference** — at least 1 instance. Write a passage with a paragraph containing two characters of the same gender; ask a question whose distractor flips the pronoun's referent.
3. **Chronology** — at least 1 instance. Best home: the Rosa Parks–style narrative or any multi-event passage; trap a wrong "which came first" answer.
4. **Tone Misidentification** — at least 1 instance. Best home: an opinion piece or passage with a clearly skeptical/sarcastic narrator.
5. **Emotional Salience** — at least 1 instance. Best home: the narrative passage (Paper Crane–style); include a wrong answer that's emotionally satisfying but textually unsupported.

---

## Section 3 — ELA Editing/Revising Trap Types

The checklist names 12 editing trap types. Easy module has only 4 R/E questions per test, so full coverage requires rotation across 3 tests minimum.

| # | Checklist trap type | Test 1 (v5) easy_module | Test 2 | Test 3 | Test 4 | Notes |
|---|---|:---:|:---:|:---:|:---:|---|
| 1 | Comma splice | ✓ (routing Q5) | | | | Present in routing only; add to easy Test 2. |
| 2 | Subject-verb disagreement | ✓ (easy Q2: collective noun) | | | | Cover variant: closer-noun rule, indefinite pronoun subject. |
| 3 | Pronoun agreement / ambiguity | — | | | | **Missing from easy.** Priority for Test 2. |
| 4 | Modifier placement (dangling) | ✓ (easy Q1) | | | | Present in easy. Rotate to misplaced (non-dangling) in Test 2. |
| 5 | Parallel structure | ✓ (easy Q4) | | | | Present. Rotate to a 3-element verb list with embedded prepositional phrases in Test 2. |
| 6 | Wrong transition logic | — | | | | **Missing from easy.** Priority for Test 2 R/E. |
| 7 | Verb tense consistency | ✓ (easy Q3 in language-learning passage) | | | | Present. Rotate variant. |
| 8 | Illogical sentence order | ✓ (routing Q5; hard Q1, Q4) | | | | Covered in routing/hard; not in easy. |
| 9 | Wordiness / redundancy | — | | | | **Missing from easy.** Priority for Test 2. |
| 10 | Concision judgment | — | | | | Often co-occurs with wordiness. Same priority. |
| 11 | Formality mismatch | — | | | | **Missing entirely.** Priority for Test 3. |
| 12 | Incorrect punctuation hierarchy | — | | | | **Missing from easy.** Semicolon/colon/dash distinctions. Priority for Test 2. |

### Priority targets for Test 2 ELA (R/E)

Replace 2 of the 4 easy-module R/E slots with:
1. **Pronoun agreement/ambiguity** — e.g., a sentence with "she" that could refer to two characters.
2. **Wrong transition logic** — e.g., "however" used where "therefore" is needed.

Across the routing + easy + hard modules, ensure each test contains:
- One concision/wordiness item
- One punctuation hierarchy item (semicolon vs comma+conjunction)

---

## Section 4 — Math Distractor Trap Types

The checklist names 5 broad error categories plus 7 cognitive trap types. v5 covers some of each.

### 4a. Error-category traps (arithmetic, algebra, geometry, word, cognitive)

| # | Error category | Specific trap | Test 1 (v5) | Test 2 | Test 3 | Test 4 | Notes |
|---|---|---|:---:|:---:|:---:|:---:|---|
| 1 | Arithmetic | Sign error | ✓ (easy Q5; named explicitly) | | | | Add to hard module. |
| 2 | Arithmetic | PEMDAS violation | ✓ (routing `order_of_operations`) | | | | Move into easy/hard. |
| 3 | Arithmetic | Decimal placement | — | | | | **Missing.** Priority for Test 2. |
| 4 | Arithmetic | Fraction operation confusion | ✓ (easy Q6 implicitly) | | | | Make explicit in Test 2. |
| 5 | Algebra | Distribution mistakes | — | | | | **Missing.** Priority for Test 2 hard module. |
| 6 | Algebra | Combining unlike terms | — | | | | **Missing.** Priority for Test 2. |
| 7 | Algebra | Reversal errors | ✓ (easy Q21 `ratio_reversal`) | | | | Covered. |
| 8 | Algebra | Exponent rule confusion | ✓ (hard Q4) | | | | Covered in hard. |
| 9 | Geometry | Perimeter vs area | ✓ (easy Q11 `last_step_trap`) | | | | Covered. |
| 10 | Geometry | Radius vs diameter | — | | | | **Missing.** Priority for Test 2. |
| 11 | Geometry | Surface area vs volume | — | | | | **Missing.** Priority for Test 2 or 3. |
| 12 | Geometry | Diagram-not-to-scale | — | | | | **Missing.** Requires figures. Address when adding diagrams. |
| 13 | Word problem | Ratio reversal | ✓ (easy Q21) | | | | Covered. |
| 14 | Word problem | Wrong operation selection | — | | | | **Missing as explicit tag.** |
| 15 | Word problem | Misreading units | ✓ (easy Q20 `unit_confusion`) | | | | Covered. |
| 16 | Word problem | Ignoring constraints | ✓ (easy Q22 hidden constraint) | | | | Covered. |

### 4b. Cognitive trap types

| # | Cognitive trap | Test 1 (v5) | Test 2 | Test 3 | Test 4 | Notes |
|---|---|:---:|:---:|:---:|:---:|---|
| 17 | Fast Pattern Match | ✓ (easy Q3, Q5; 2 instances) | | | | Covered. Add to hard module. |
| 18 | Last-Step Trap | ✓ (easy Q3, Q5, Q11; 3 instances) | | | | Well covered. |
| 19 | Hidden Constraint | ✓ (easy Q22) | | | | Covered. Add to hard. |
| 20 | Estimation Failure | ✓ (easy Q9, Q20, Q24) | | | | Well covered. |
| 21 | Visual Assumption | — | | | | **Missing.** Requires figures. Address when adding diagrams. |
| 22 | Shortcut Overreach | — | | | | **Missing.** E.g., applying difference-of-squares to non-difference. |
| 23 | Working Memory Collapse | ✓ implicitly (multi-step questions) | | | | Strengthen by adding 4+ step problems in Test 2 hard. |

### Priority targets for Test 2 Math

1. **Decimal placement** error — at least 1 distractor showing the wrong decimal position.
2. **Distribution mistakes** in algebra — e.g., correct answer is `5x − 15`, trap is `5x − 3`.
3. **Combining unlike terms** — distractor shows `3x + 2y` becoming `5xy` or `5`.
4. **Radius/diameter confusion** — geometry question where the trap is using diameter where radius is needed.
5. **Shortcut Overreach** — algebra question where a familiar identity (e.g., difference of squares) doesn't actually apply.

When you start adding figures/diagrams:
- **Visual Assumption** trap (diagram suggests a relationship not stated)
- **Diagram-not-to-scale** trap
- **Surface area vs volume** confusion (3D figures)

---

## Section 5 — Skill coverage (already balanced, here for reference)

These are the cognitive skills sampled. v5 hits all five in every module; ensure each new test maintains this balance.

### ELA skills

| Skill | Easy module (v5) | Hard module (v5) | Target per module |
|---|:---:|:---:|---|
| literal_comprehension | 4 | — | At least 3 |
| inference_analysis | 10 | 16 | 6–12 |
| rhetoric_organization | 6 | 6 | 4–8 |
| vocabulary | 4 | 4 | 3–5 |
| grammar_mechanics (R/E) | 4 | 2 | 3–5 |

### Math skills

| Skill | Easy module (v5) | Hard module (v5) | Target per module |
|---|:---:|:---:|---|
| number_operations | 6 | 4 | 4–7 |
| algebraic_reasoning | 6 | 7 | 4–7 |
| geometric_reasoning | 5 | 6 | 4–7 |
| data_probability | 5 | 4 | 4–6 |
| multistep_reasoning | 6 | 7 | 4–7 |

---

## Section 6 — Passage-type rotation

Easy-module passages should vary in genre and structure across tests so students see the full range of SHSAT passage types.

| Passage type | Test 1 (v5) | Test 2 | Test 3 | Test 4 | Notes |
|---|:---:|:---:|:---:|:---:|---|
| Informational science | ✓ Honeybees | | | | |
| Informational geology/earth science | ✓ Volcanoes | | | | |
| Historical narrative | ✓ Rosa Parks | | | | |
| Realistic fiction | ✓ Paper Crane | | | | |
| Persuasive / argumentative | — | priority | | | **Missing.** Op-ed style with clear author stance — needed for tone misidentification traps. |
| Literary nonfiction / memoir | — | | priority | | First-person reflective; good for inference and tone questions. |
| Comparative passages (paired) | — | | | priority | Two short passages on same topic; tests synthesis across sources. |
| Procedural / how-it-works | — | priority | | | Step-by-step explanation; good for chronology traps. |

---

## Section 7 — Per-test build checklist

When building any new test, walk this checklist before publishing:

### Structural

- [ ] 5 grid-ins per math module (easy, hard)
- [ ] 4 passages in easy-module ELA, 500–700 words each
- [ ] At least 3 passages in hard-module ELA (typically longer, 700–900 words)
- [ ] All 5 ELA skills represented in every module
- [ ] All 5 math skills represented in every module
- [ ] Difficulty curve: easy → medium → hard within each module
- [ ] No more than 2 consecutive same-skill questions

### Distractor variety

- [ ] No question has 3 identical distractor tags (e.g., all `computation_error`)
- [ ] `unsupported` ≤ 20% of ELA distractors
- [ ] `computation_error` ≤ 30% of math distractors
- [ ] At least 6 distinct distractor types per module

### Trap coverage (consult matrix above)

- [ ] At least 3 trap types from "priority for next test" rows of this matrix
- [ ] No trap type from Section 2 (ELA RC) absent in three consecutive tests
- [ ] No trap type from Section 3 (R/E) absent in three consecutive tests
- [ ] No trap type from Section 4 (Math) absent in three consecutive tests

### Calibration

- [ ] Easy module questions roughly match the "easy end" of real SHSAT (Form A/B references)
- [ ] Hard module questions match real SHSAT mid-to-late questions
- [ ] Routing module spans the full real-SHSAT difficulty range

### Quality control

- [ ] Every grid-in answer is a clean number that fits the grid (positive or signed, decimals OK, fractions OK if you allow them)
- [ ] Every MC question has one unambiguously correct answer
- [ ] Every distractor corresponds to a *plausible* student error, not a random wrong number
- [ ] No question requires outside knowledge beyond the SHSAT scope

---

## Section 8 — Internal label glossary

A single source of truth for distractor labels. Add to this glossary whenever you introduce a new label.

### ELA labels

| Label | Definition | Use when |
|---|---|---|
| `unsupported` | The answer makes a claim the passage doesn't make. | Catch-all; **use sparingly.** Prefer more specific labels below when possible. |
| `opposite` | The answer states the reverse of what the passage says. | Common in inference/main-idea questions. |
| `extreme_language` | Wrong because of words like "all," "never," "always," "completely." | Easy to spot trigger words. |
| `too_broad` | Overgeneralizes a specific passage claim. | Synonym for "overgeneralization." |
| `too_narrow` | The answer is one true detail but doesn't capture the full point of the question. | Common in main-idea and rhetorical-purpose questions. |
| `too_literal` | Reads a figurative passage element as literal fact. | Vocabulary and figurative-language questions. |
| `misidentified_detail` | Confuses one detail in the passage with another. | Comprehension questions where a passage has multiple parallel facts. |
| `distortion` | Combines or mangles passage claims to make something the passage doesn't quite say. | Inference questions. |
| `surface_match` | Uses words from the passage but the meaning doesn't match the question. | Effective trap because it rewards skimming. |
| `inference_leap` | Goes beyond what the passage supports. | Inference questions. |
| `causal_confusion` | Confuses cause/effect, correlation/causation, or sequence. | Science and historical passages. |
| `true_but_irrelevant` | The claim is factually correct but doesn't answer the question. | Authorial-purpose questions especially. |
| `wrong_fix` | (R/E) The proposed edit doesn't fix the error or introduces a new error. | All R/E distractors. |
| `overcorrection` | (R/E) The edit changes something that was already correct. | All R/E distractors. |
| **TO ADD** | | |
| `partial_correctness` | One part of the answer matches the passage; another part doesn't. | Multi-clause answers. |
| `scope_shift` | Moves from specific → general or local → global. | Inference questions. |
| `emotional_salience` | The answer is emotionally appealing but textually unsupported. | Narrative passages. |
| `pronoun_reference` | The answer attributes something to the wrong character/object. | Passages with multiple referents. |
| `chronology` | The answer misorders events. | Narrative or historical passages. |
| `tone_misidentification` | The answer misreads authorial tone. | Opinion/argumentative passages. |

### Math labels

| Label | Definition | Use when |
|---|---|---|
| `computation_error` | A specific arithmetic slip. | **Use sparingly.** Prefer the more specific labels below. |
| `wrong_formula` | The student applies the wrong formula. | Geometry, algebra. |
| `partial_answer` | Stopped at an intermediate step. | Multi-step problems where the intermediate has a name. |
| `partial_step` | Skipped a step in the procedure. | Multi-step problems. |
| `last_step_trap` | Computed all the math right but reported the wrong final quantity (e.g., area when perimeter was asked). | Strongly recommended for geometry and percent problems. |
| `fast_pattern_match` | Student recognizes a familiar pattern and applies the wrong procedure. | Order-of-operations, absolute value, fraction problems. |
| `hidden_constraint` | (Implicit in the question) Student ignored an explicit condition like "positive integer" or "largest." | Word problems with constraints. |
| `estimation_failure` | Picked a numerically reasonable answer without computing. | Rate/distance/percent problems. |
| `sign_error` | Mishandled a negative sign. | Arithmetic with negatives. |
| `ratio_reversal` | Swapped two quantities in a ratio or word problem. | Word problems. |
| `unit_confusion` | Answer in wrong units (hours vs minutes, cm vs cm², etc.). | Rate problems, geometry. |
| `wrong_concept` | Applied the wrong concept (e.g., used range when mean was asked). | Data/statistics problems. |
| `proportion_inversion` | Inverted a proportion. | Proportion and percent problems. |
| `off_by_operation` | Used the wrong operation (added instead of subtracted, etc.). | Word problems. |
| `misread_question` | Answered a different question than the one asked. | Any. |
| `order_of_operations` | PEMDAS violation. | Arithmetic. |
| `unsimplified` | Answer is mathematically equivalent but not in lowest terms. | Fractions. |
| `surface_match` | Picked an answer that looks like the question's surface form. | Comparison questions. |
| `misidentified_detail` | Confused two named values in the problem. | Geometry with multiple labeled elements. |
| `opposite` | Sign or direction reversed. | Sequence, inequality questions. |
| **TO ADD** | | |
| `distribution_error` | Failed to distribute correctly. | Algebra. |
| `combining_unlike_terms` | Combined terms that aren't like. | Algebra. |
| `radius_diameter_confusion` | Used diameter where radius was needed, or vice versa. | Circle geometry. |
| `surface_volume_confusion` | Used surface area formula for volume question, or vice versa. | 3D geometry. |
| `shortcut_overreach` | Applied an identity/shortcut where it doesn't apply. | Algebra. |
| `visual_assumption` | Treated a diagram feature as given when it wasn't stated. | Geometry with figures. |

---

## Section 9 — Recommended build order

If you're planning Tests 2–4, here's a suggested rotation that ensures coverage within 4 tests:

### Test 2 — priorities

- **ELA RC traps:** Partial Correctness, Pronoun Reference, Chronology
- **ELA R/E traps:** Pronoun agreement, Wrong transition, Punctuation hierarchy
- **Math traps:** Decimal placement, Distribution mistakes, Radius/diameter confusion
- **Passage genre to add:** Persuasive/argumentative + Procedural/how-it-works
- **Cognitive traps to strengthen:** Shortcut Overreach, more Working Memory Collapse

### Test 3 — priorities

- **ELA RC traps:** Tone Misidentification, Emotional Salience, second pass at Inference Leap and Causal Confusion
- **ELA R/E traps:** Wordiness/concision, Formality mismatch
- **Math traps:** Surface area vs volume, Combining unlike terms, second pass at Fast Pattern Match in hard module
- **Passage genre to add:** Literary nonfiction / memoir
- Begin adding **figures and diagrams** → unlocks Visual Assumption and Diagram-not-to-scale traps

### Test 4 — priorities

- Round out any traps still missing from the matrix
- **Passage genre to add:** Comparative paired passages
- Focus on **higher-discrimination items** that separate top scorers (the 90th–99th percentile range)
- Stress-test timing: include more time-trap items

---

*Last updated for v5 of Test 1. Update this document each time a new test ships.*
