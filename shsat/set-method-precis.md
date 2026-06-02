# The Set Method — Baseline Precis
*A semantic-set framework for SHSAT Reading Comprehension*

---

## 1. Core claim

SHSAT reading-comprehension questions do not test "reading" as a diffuse skill. Each question presents the test-taker with a small number of candidate statements and asks them to decide, for each one, whether it **belongs to a precisely defined set of meaning**. Mastering the section is therefore mastering a single, learnable operation — *membership testing against a bounded set* — applied over and over under time pressure.

This claim is not theoretical. It is recoverable directly from the official answer rationales in the sample tests, which justify every wrong answer as a failure of set membership: an option "does not discuss," "fails to convey," "acknowledges X but does not describe Y," or describes a relationship the text reverses. The scoring logic *is* set logic.

## 2. The one correction: what the universal set really is

The intuitive move is to let the passage be a universal set **U = "everything the passage means."** This is too wide and will actively cause errors.

Every test form's directions instruct the student to base answers **only on the content within the text**. The operative universe is therefore narrower:

> **U = { claims the passage explicitly states or directly supports }**

Everything outside that boundary — true facts about the world, reasonable real-life associations, ideas the topic "feels related to" — is *outside U*, no matter how plausible. The most seductive distractors live exactly there. Teaching the correct boundary of U is the highest-leverage single lesson in the method.

## 3. The operations (mapped to real SHSAT question types)

Every question type reduces to a set operation over U. Examples below are real items in the project's practice tests, cited so they can be located and used directly.

- **Supporting-evidence questions** → *find the member of a subset.*
  "Which sentence supports the idea that some species adjust to change?" asks: from the sentences in the passage, identify the one in `{ sentences that support proposition P }`. *(Form A 2024, Q55; Q15; Q53.)*

- **"Most relevant support" questions** → *find the maximal element of a subset.* Several options may technically belong; the answer is the one with the strongest membership. This is a ranking, not a yes/no. *(Form A 2024, Q53.)*

- **Vocabulary / words-in-context** → *intersection.*
  meaning-here = `{ possible senses of the word } ∩ { senses the surrounding sentence allows }`. The wrong answers are usually valid dictionary senses that fall outside the second set. *(Form B 2024, Q10 — "recognized" / "prestigious"; Form A 2024, Q40 — "clings to life" / "stripped of bark".)* Notably, Form B 2025 (Q18–20) contains a passage whose subject is this exact skill, useful as a meta-lesson.

- **Central-idea questions** → *test membership in a single privileged subset.*
  "The details in paragraph X convey a central idea by suggesting that…" asks which option is in `{ statements that are central ideas of the passage }`. The classic trap is an option that is a *true detail* of the passage (inside U) but is *not central* (outside the target subset). *(Form A 2024, Q10, Q11, Q41.)*

- **Summary questions** → *the subset that is complete-and-only.* The correct summary includes the essential members and excludes non-members; wrong summaries either drop an essential element or smuggle in a non-member. *(Form B 2025, Q18.)*

- **Inference / "because" questions** → *membership via entailment.* The answer is the proposition U *forces* to be true, even if unstated. *(Form B 2025, Q19.)*

- **Structure / function / tone questions** → *relations, handled at the evaluation step.* "How does paragraph 4 contribute to paragraph 1?" or "the author's use of cause and effect emphasizes…" are about *relations between parts*, which set-membership models only loosely (see §5). But the final step is still a membership test: of each option, "is this claim supported by the text?" *(Form A 2024, Q12, Q54; Q39.)*

## 4. The distractor taxonomy — the heart of the method

This is the part to build the most material around, because it is the most trainable and the most gradeable. Across the sample tests, **every wrong answer falls into one of four set-relations.** Teaching students to *name which one* is the skill.

| Distractor type | Set relation | How it looks | Real example pattern |
|---|---|---|---|
| **Out of scope** | not in U at all | A claim about something the passage never addresses. Rationale language: "never addresses," "does not discuss." | Form B 2025 Q19-B: the excerpt never addresses how earlier research was conducted. |
| **True but off-target** | in U, outside the question's subset | A real, supported detail that doesn't satisfy the *specific* condition the stem asks for (e.g., true detail that isn't the *central* idea). | Form A 2024 Q10-G: a real comparison in the text that "fails to convey the central idea." |
| **Partial / overreach** | overlaps the subset but isn't fully in it | Part of the claim is supported, part isn't — or a supported idea stated too strongly/broadly. | Form A 2024 Q11-B: passage acknowledges one half of the claim "but does not describe" the other half. |
| **Contradiction / reversal** | in the complement of U | The claim inverts or misattributes a relationship the text states (cause↔effect, teaching↔assessing). | Form B 2025 Q19-C: the task was used "not as a teaching tool but rather to assess." |

The **correct answer** is always the unique option lying in the intersection of *(what U supports)* and *(the precise condition the stem defines)*. Naming the four types converts elimination from intuition ("this one feels wrong") into a rule-governed procedure ("this is a reversal").

## 5. Scope and limits (state these honestly)

The Set Method is a near-complete model of **answer evaluation** — deciding among given options. It is a *partial* model of **comprehension** — building U in the first place by reading the passage. Two boundaries to respect:

1. **Construction vs. adjudication.** The frame tells a student how to judge options once U exists; it says little about how to read a dense passage and assemble U. Pair every set-logic lesson with ordinary close-reading instruction (paragraph purpose, signposting, paraphrasing on the fly).
2. **Membership vs. relation.** Tone, author's-purpose, and text-structure questions are about *relations and functions* between parts of the text. These can be forced into set language, but it's awkward; treat them as a distinct sub-skill where the set frame only governs the final option check.

Positioning follows directly: market this as a **rule-governed system for never being fooled by a distractor**, not as a total theory of reading. The first is defensible and distinctive; the second invites easy counterexamples.

## 6. From precis to lessons (how this seeds the curriculum)

Each section above is a module. A suggested progression:

1. **Defining U.** Drills that sort statements into *stated / directly supported / true-but-unsupported / contradicted*, using short passages. This installs the §2 correction first, because it prevents the most common error.
2. **The four distractor types.** Students are shown a question + the four wrong answers and must *tag each one* by type before choosing. (This tagging schema maps cleanly onto a database field and an interactive UI — drag each option into one of four labeled bins.)
3. **One operation per question type.** A unit each for supporting-evidence (find a member), vocabulary (intersection), central idea (privileged subset), summary (complete-and-only), inference (entailment).
4. **Venn scaffolding.** Use two- and three-circle Venn visuals as the persistent mental model — "inside the circle / outside / overlap" — rather than heavy symbolic notation, which adds cognitive load for the grade level. Introduce `∩`, `⊆` only as an optional layer for students who like it.
5. **Mixed timed sets.** Students apply the full procedure under time pressure, then review *which set-relation* each missed distractor was — turning error review into a structured, repeatable loop.

**Platform note:** because every operation is discrete and checkable (a statement either is or isn't in a set; a distractor is exactly one of four types), the method is unusually well-suited to auto-graded interactive exercises rather than free-text reading practice. The distractor taxonomy in §4 can serve directly as both a tagging schema for content authoring and the answer key for "classify this trap" exercises.

## 7. Worked example (end to end)

*Question type:* central idea. *Stem condition:* "details in this paragraph convey a **central idea** by suggesting that…"

1. **Bound U.** What does the paragraph state or directly support? (Build the supported-claims set.)
2. **Read the stem's target subset.** Not "any true detail" — specifically `{ central ideas }`. A true-but-minor detail is disqualified.
3. **Membership-test each option.**
   - Outside U (topic not addressed) → *out of scope*, eliminate.
   - True detail, but not central → *true but off-target*, eliminate.
   - Half supported → *partial*, eliminate.
   - Reverses a stated relationship → *contradiction*, eliminate.
4. **Confirm the survivor** lies in `(U) ∩ ({ central ideas })`. Mark it.

The student never asks "which feels best." They ask, four times, "is this in the set, and is it in the *right* set?" — which is the entire discipline the SHSAT is testing.

---

*Baseline grounded in: SHSAT Practice Tests Forms A & B (2023–2025), passages including "A Memory Revolution," the bristlecone-pine excerpt, the non-native-species excerpt, "The Food Business Incubator" (La Cocina), the Niagara Falls excerpt, and the exercise-and-vocabulary study.*
