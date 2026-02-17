from __future__ import annotations

import os
import yaml

from scoring import score_answers


def load_questions(path: str | None = None) -> list[dict]:
    if path is None:
        base_dir = os.path.dirname(__file__)
        path = os.path.join(base_dir, "questions.yaml")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["questions"]


def main() -> None:
    questions = load_questions()

    # Fake answers for a sanity check.
    # Edit these to simulate different users.
    answers = {
        "UH_PU_S1_01": "A",  # paralysis_until_certainty
        "UH_PU_S2_02": "A",  # paralysis_until_certainty
        "UH_PU_S2_03": "A",  # paralysis_until_certainty
        "UH_PC_S1_01": "B",  # premature_closure
        "UH_PV_S1_01": "A",  # probability_as_vibe
        "MA_MR_S1_01": "A",  # model_reification
        "MA_AB_S1_01": "A",  # assumption_blindness
        "MA_MS_S1_01": "A",  # model_shopping
        "CR_CC_S1_01": "A",  # correlation_causation_leap
        "CR_ND_S1_01": "A",  # narrative_dominance
        "CR_NI_S1_01": "A",  # no_intervention_thinking
        "AC_AT_S1_01": "A",  # anecdote_trap
        "AC_TL_S1_01": "A",  # theory_lock_in
        "AC_LC_S1_01": "A",  # level_confusion
        "EH_DR_S1_01": "A",  # defensive_rejection
        "EH_AS_S1_01": "A",  # authority_surrender
        "EH_IF_S1_01": "A",  # identity_fusion
    }

    result = score_answers(questions=questions, answers=answers, top_k=2)

    print("\nTop breakpoints:")
    for i, bp in enumerate(result.top_breakpoints, start=1):
        print(f"  {i}. {bp}")

    print("\nScores (descending):")
    ranked = sorted(result.scores.items(), key=lambda x: x[1], reverse=True)
    for bp, n in ranked:
        if n > 0:
            print(f"  {bp:28s} {n}")

    print("\nAligned counts (only nonzero):")
    for bp, n in result.aligned_counts.items():
        if n > 0:
            print(f"  {bp:28s} {n}")

    print("\nDimension totals:")
    for dim, n in result.dimension_totals.items():
        print(f"  {dim:22s} {n}")


if __name__ == "__main__":
    main()
