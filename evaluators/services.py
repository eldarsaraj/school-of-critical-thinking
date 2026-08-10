"""
Service-layer orchestration for essay evaluation.
Computes all deterministic metrics then calls the NOOA agent.
"""
from __future__ import annotations


async def evaluate_essay(
    essay: str,
    prompt: str,
    requirements: list[str] | None = None,
):
    """
    Compute all deterministic metrics for the essay, then call the NOOA
    EssayEvaluator agent.  Returns a validated EssayEvaluation Pydantic object.

    Args:
        essay:        The full student essay text.
        prompt:       The essay prompt as shown to the student.
        requirements: Explicit list of scoring requirements.
                      If None, the whole prompt is used as a single requirement.
    """
    import evaluators.apps as _app
    from .apps import get_embedder, get_evaluator
    from .metrics import (
        basic_counts,
        sentence_length_stats,
        top_repeated_content_words,
        vague_word_density,
        weak_verb_rate,
        sentence_opener_variety,
        sentence_type_mix,
        compute_mtld,
        spelling_analysis,
        concreteness_mean,
        find_weak_transitions,
    )

    if not essay or not essay.strip():
        raise ValueError("Essay text is empty.")

    if requirements is None:
        requirements = [prompt.strip()]

    # --- Deterministic metrics ---
    counts = basic_counts(essay)
    length_stats = sentence_length_stats(essay)
    spp = round(counts["sentence_count"] / max(counts["paragraph_count"], 1), 1)
    repeated = top_repeated_content_words(essay)
    vague = vague_word_density(essay)
    weak = weak_verb_rate(essay)
    opener_var = sentence_opener_variety(essay)
    type_mix = sentence_type_mix(essay)
    mtld_score = compute_mtld(essay)
    spelling = spelling_analysis(essay)
    conc = concreteness_mean(essay, _app.CONCRETENESS_DICT)
    transitions = find_weak_transitions(essay, get_embedder())

    # --- NOOA agent ---
    result = await get_evaluator().evaluate(
        essay=essay,
        prompt=prompt,
        requirements=requirements,
        word_count=counts["word_count"],
        sentence_count=counts["sentence_count"],
        paragraph_count=counts["paragraph_count"],
        sentence_length_mean=length_stats["sentence_length_mean"],
        sentence_length_sd=length_stats["sentence_length_sd"],
        sentences_per_paragraph_mean=spp,
        top_repeated_words=repeated,
        vague_word_density=vague,
        weak_verb_rate=weak,
        sentence_opener_variety=opener_var,
        sentence_type_mix=type_mix,
        mtld=mtld_score,
        spelling_error_rate=spelling["spelling_error_rate"],
        spelling_errors=spelling["spelling_errors"],
        concreteness_mean=conc,
        weak_transitions=transitions,
    )
    return result
