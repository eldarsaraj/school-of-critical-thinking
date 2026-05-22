# SHSAT Adaptive Practice Test — Design Specification

## Overview

Each practice test mirrors the format of the official NYC SHSAT exactly in terms of question count,
section structure, and question types. The adaptive layer (multistage routing) is invisible to the
student — they simply see 57 questions per section, just as they would on the real test.

---

## Real SHSAT Format (source of truth)

| Section | Subsection              | Questions | Type            |
|---------|-------------------------|-----------|-----------------|
| ELA     | Revising/Editing        | 1–9       | Multiple choice |
| ELA     | Reading Comprehension   | 10–57     | Multiple choice |
| Math    | Grid-In                 | 58–62     | Numeric (grid)  |
| Math    | Multiple Choice         | 63–114    | Multiple choice |

- **Total:** 114 questions (57 ELA + 57 Math)
- **Time:** 180 minutes total; students allocate time between sections as they choose
- **Scoring:** No penalty for wrong answers — answer every question

---

## Adaptive Structure (Multistage)

### How it works (student experience)

1. Student starts ELA. They see 29 questions (routing stage) — numbered 1–29.
2. Based on their routing score, they are silently assigned to Easy or Hard ELA module.
3. They continue with 28 more ELA questions (module stage) — numbered 30–57.
4. Student moves to Math. Same process: 29 routing questions, then 28 module questions.
5. Student never sees the words "routing," "easy module," or "hard module."

### Routing is independent per section

A student can be in Hard ELA and Easy Math, or any other combination. ELA routing score
only determines ELA module; Math routing score only determines Math module.

### Routing threshold

- Score ≥ 60% on routing (≥ 18/29 correct) → **Hard module**
- Score < 60% on routing (≤ 17/29 correct) → **Easy module**

---

## Question Counts Per Stage

### ELA

| Stage        | Revising/Editing | Reading Comprehension | Total |
|--------------|------------------|-----------------------|-------|
| Routing      | 5                | 24                    | 29    |
| Easy module  | 4                | 24                    | 28    |
| Hard module  | 4                | 24                    | 28    |
| **Section total** | **9**       | **48**                | **57** |

### Math

| Stage        | Grid-In | Multiple Choice | Total |
|--------------|---------|-----------------|-------|
| Routing      | 3       | 26              | 29    |
| Easy module  | 2       | 26              | 28    |
| Hard module  | 2       | 26              | 28    |
| **Section total** | **5** | **52**        | **57** |

---

## Question Type Rules

### ELA — Revising/Editing (R&E)

Matches the real test structure:
- **Part A** (standalone): Each question presents a single sentence or short paragraph.
  Student identifies and corrects a grammar/mechanics/style error.
- **Part B** (passage-based): A short passage with numbered sentences. Questions ask
  the student to revise or correct specific sentences within it.
- Answer choices labeled **A/B/C/D** for Part A, **E/F/G/H** for Part B
  (matching real SHSAT convention).

### ELA — Reading Comprehension (RC)

- 4–6 passages per stage, each 250–600 words
- 4–10 questions per passage
- All questions for a passage must be in the **same stage** — never split across routing
  and module
- Passage topics: literary fiction, informational/expository, paired passages,
  poetry (occasional)
- Question types: literal comprehension, inference, vocabulary in context,
  author's purpose, rhetoric/organization

### Math — Grid-In

- Numeric answers only; no answer choices
- Student writes answer in grid (integer or decimal)
- No negative answers on real SHSAT
- Answers should be clean integers or simple decimals when possible

### Math — Multiple Choice

- Answer choices labeled **A/B/C/D**
- Covers: number operations, algebra, geometry, data/statistics, word problems
- Grid-in questions come **before** multiple choice within each stage,
  matching real test order

---

## Difficulty Distribution

### Routing stage (must span full ability range to predict accurately)

| Difficulty | Target % |
|------------|----------|
| Easy       | 40%      |
| Medium     | 40%      |
| Hard       | 20%      |

### Easy module (for students who scored < 60% on routing)

| Difficulty | Target % |
|------------|----------|
| Easy       | 50%      |
| Medium     | 40%      |
| Hard       | 10%      |

### Hard module (for students who scored ≥ 60% on routing)

| Difficulty | Target % |
|------------|----------|
| Easy       | 10%      |
| Medium     | 40%      |
| Hard       | 50%      |

---

## Scoring

### Raw score

Raw score = number of correct answers in routing stage + module stage (combined).
Maximum raw score per section = 57.

### Scaled score

Each section scaled from **200 to 400** using a conversion table.
Two separate tables exist per section — one for Easy module takers, one for Hard module takers —
because the same raw score has different meaning depending on which module was taken.

**Principle:**
- Hard module takers have a higher floor and ceiling for the same raw score
- Overlap zone exists (~raw 20–25) where a strong Easy module score approximates
  a weak Hard module score
- Easy module max scaled score: ~340 (prevents ceiling effect from masking ability gaps)
- Hard module min scaled score: ~250 (students who struggled still get credit for attempting harder material)

Conversion tables will be calibrated once test content is finalized and validated.

### Composite score

**Composite = ELA scaled + Math scaled (range: 400–800)**

Displayed on the dashboard alongside real cutoff scores for all 8 specialized high schools
(already seeded in the database).

### Skill breakdown

In addition to section scores, each result shows accuracy by skill:

**ELA skills:** Grammar & Mechanics, Rhetoric & Organization, Literal Comprehension,
Inference & Analysis, Vocabulary in Context

**Math skills:** Number & Operations, Algebraic Reasoning, Geometric Reasoning,
Data & Probability, Multi-step Reasoning

---

## YAML Import Format

```yaml
title: "Practice Test 1"
is_adaptive: true
routing_threshold: 0.60
is_free: true
is_published: false

ela:
  - question_number: 1
    stage: routing          # routing | easy_module | hard_module
    question_type: multiple_choice
    skill: grammar_mechanics
    difficulty: easy
    passage_group_id: ""    # empty for standalone R&E
    passage_title: ""
    passage_text: ""
    question_text: "..."
    choice_a: "..."
    choice_b: "..."
    choice_c: "..."
    choice_d: "..."
    correct_answer: "A"
    explanation: "..."
    distractors:
      B: wrong_fix
      C: overcorrection
      D: unsupported

math:
  - question_number: 1
    stage: routing
    question_type: grid_in
    skill: number_operations
    difficulty: medium
    question_text: "..."
    correct_answer: "42"
    explanation: "..."
```

### Question numbering in YAML

- Number questions **within each stage independently** (routing Q1–29, easy Q1–28, hard Q1–28)
- The database `unique_together` constraint is `(test, section, stage, question_number)`
- Student-facing numbering (1–57) is computed at display time by concatenating routing + module

---

## Content Review Checklist (before publishing)

- [ ] Correct answer is actually correct (verify independently)
- [ ] All 4 wrong answers have a distractor trap tagged
- [ ] Passage questions: all questions reference the passage accurately
- [ ] Passage group IDs are consistent across questions sharing a passage
- [ ] Grid-in answers are positive integers or simple decimals
- [ ] Difficulty ratings feel right relative to other questions in the same stage
- [ ] Explanations explain the reasoning, not just restate the answer
- [ ] R&E Part B answer choices use E/F/G/H, not A/B/C/D
- [ ] Question count per stage matches spec (routing: 29, module: 28)
- [ ] Subsection counts match spec (ELA: 5+4 R&E, 24+24 RC; Math: 3+2 grid-in, 26+26 MC)
