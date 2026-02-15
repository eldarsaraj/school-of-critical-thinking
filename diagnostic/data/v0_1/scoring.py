from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

ALL_BREAKPOINTS: List[str] = [
    # Uncertainty Handling
    "paralysis_until_certainty",
    "premature_closure",
    "probability_as_vibe",
    # Model Awareness
    "model_reification",
    "assumption_blindness",
    "model_shopping",
    # Causal Reasoning
    "correlation_causation_leap",
    "narrative_dominance",
    "no_intervention_thinking",
    # Abstraction Control
    "anecdote_trap",
    "theory_lock_in",
    "level_confusion",
    # Epistemic Humility
    "defensive_rejection",
    "authority_surrender",
    "identity_fusion",
]

BREAKPOINT_ORDER: Dict[str, int] = {bp: i for i, bp in enumerate(ALL_BREAKPOINTS)}


@dataclass(frozen=True)
class ScoreResult:
    top_breakpoints: List[str]
    scores: Dict[str, int]
    aligned_counts: Dict[str, int]
    dimension_totals: Dict[str, int]


def score_answers(
    questions: List[dict],
    answers: Dict[str, str],
    top_k: int = 2,
) -> ScoreResult:
    """
    questions: list of question dicts from questions.yaml
    answers:   {question_id: choice_id} where choice_id in {"A","B","C","D"}
    """
    scores = {bp: 0 for bp in ALL_BREAKPOINTS}
    aligned_counts = {bp: 0 for bp in ALL_BREAKPOINTS}
    dimension_totals: Dict[str, int] = {}

    # index questions by id for safety
    q_by_id = {q["id"]: q for q in questions}

    for qid, choice_id in answers.items():
        if qid not in q_by_id:
            continue  # ignore unknown question ids

        q = q_by_id[qid]
        dim = q["dimension"]
        dimension_totals[dim] = dimension_totals.get(dim, 0) + 1

        # find selected choice
        selected = None
        for ch in q["choices"]:
            if ch["id"] == choice_id:
                selected = ch
                break
        if selected is None:
            continue  # ignore invalid choice ids

        tag = selected["tag"]

        # only count known breakpoint tags
        if tag not in scores:
            continue

        scores[tag] += 1
        if tag == q.get("breakpoint"):
            aligned_counts[tag] += 1

    def dim_total_for(bp: str) -> int:
        # map breakpoint to its dimension by scanning questions (best-effort)
        # If a breakpoint never appears as a question.breakpoint, fall back to 0.
        for q in questions:
            if q.get("breakpoint") == bp:
                return dimension_totals.get(q["dimension"], 0)
        return 0

    ranked = sorted(
        ALL_BREAKPOINTS,
        key=lambda bp: (
            scores[bp],
            dim_total_for(bp),
            aligned_counts[bp],
            -BREAKPOINT_ORDER[bp],  # stable deterministic tie-break
        ),
        reverse=True,
    )

    top_breakpoints = ranked[:top_k]
    return ScoreResult(
        top_breakpoints=top_breakpoints,
        scores=scores,
        aligned_counts=aligned_counts,
        dimension_totals=dimension_totals,
    )
