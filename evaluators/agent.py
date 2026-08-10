"""
NOOA EssayEvaluator agent + EssayEvaluation Pydantic model.
"""

from typing import Dict, List
from pydantic import BaseModel, Field


class EssayEvaluation(BaseModel):
    # Basic counts
    word_count: int
    sentence_count: int
    paragraph_count: int

    # Lexical
    mtld: float = Field(
        ..., description="Lexical diversity (MTLD). Higher = more varied vocabulary."
    )
    vague_word_density: float = Field(..., description="Proportion of vague words.")
    weak_verb_rate: float = Field(..., description="Share of weak verbs.")
    top_repeated_words: List[str] = Field(
        ..., description="Most repeated content words (excluding stop words)."
    )
    concreteness_mean: float = Field(
        ..., description="Average concreteness (Brysbaert 1–5 scale)."
    )

    # Sentence structure
    sentence_length_mean: float
    sentence_length_sd: float = Field(
        ..., description="Standard deviation of sentence lengths."
    )
    sentence_opener_variety: float = Field(
        ..., description="Variety of sentence openings (0–1)."
    )
    sentence_type_mix: Dict[str, int] = Field(
        ..., description="Counts of simple/compound/complex sentences."
    )

    # Organization
    sentences_per_paragraph_mean: float
    weak_transitions: List[str] = Field(
        ..., description="Descriptions of the weakest sentence-to-sentence transitions."
    )

    # Development / Prompt coverage
    on_prompt_relevance: float = Field(
        ..., description="0–1 how on-topic the essay is."
    )
    prompt_coverage: Dict[str, float] = Field(
        ..., description="Requirement text → coverage score 0–1."
    )

    # Mechanics
    spelling_error_rate: float = Field(
        ..., description="Spelling errors per 100 words."
    )
    spelling_errors: List[str] = Field(
        ..., description="List of misspelled words found."
    )
    grammar_flags: List[str] = Field(
        default_factory=list,
        description="Grammar/punctuation issues. Empty until LanguageTool is wired.",
    )

    # LLM-generated
    feedback: str = Field(
        ...,
        description="Short, constructive natural-language feedback for the student.",
    )


def build_evaluator(llm):
    """Return an EssayEvaluator instance bound to the given LLM client."""
    from nooa import Agent, strategy
    from nooa.strategies import PredictStrategy

    class EssayEvaluator(Agent, llm=llm):
        """You are an experienced writing coach preparing students for the Hunter College High School entrance exam essay.

        Hunter readers look for:
        - A clear, focused story that fully answers every part of the prompt
        - Specific, concrete details that let the reader picture the scene
        - Genuine reflection on what the experience showed the writer about himself or herself
        - Smooth flow between sentences and ideas
        - Varied sentence structure and precise word choice

        Your feedback must help a middle-school student improve on exactly these points.
        """

        @strategy(PredictStrategy())
        async def evaluate(
            self,
            essay: str,
            prompt: str,
            requirements: list[str],
            word_count: int,
            sentence_count: int,
            paragraph_count: int,
            sentence_length_mean: float,
            sentence_length_sd: float,
            sentences_per_paragraph_mean: float,
            top_repeated_words: list[str],
            vague_word_density: float,
            weak_verb_rate: float,
            sentence_opener_variety: float,
            sentence_type_mix: dict[str, int],
            mtld: float,
            spelling_error_rate: float,
            spelling_errors: list[str],
            concreteness_mean: float,
            weak_transitions: list[str],
        ) -> EssayEvaluation:
            """Evaluate the student essay for the Hunter College High School entrance exam.

            You are given accurate quantitative measurements. Use them exactly; do not change them.

            For prompt_coverage:
            - Score each of the provided requirements from 0.0 to 1.0.
            - Use the exact requirement text as the dictionary key.

            For on_prompt_relevance: give a single 0–1 score.

            FEEDBACK RULES (very important):
            - Write 4–6 sentences directly to the student.
            - Start with one specific strength that would impress a Hunter reader (mention a concrete detail or a prompt requirement that was handled well).
            - Then give one clear, actionable improvement tied to the numbers you received.
              Good targets: low prompt-coverage scores, weak transitions, low concreteness,
              high vague-word or weak-verb rates, low sentence-opener variety.
            - If a prompt requirement scored below 0.75, explicitly tell the student what is still missing.
            - Use intuitive terms for the benchmarks, such as Essay length, Stay on prompt, Specific details, Spelling, Flow of ideas,
            so users can understand the feedback without needing to know the underlying metrics.
            - Keep the tone encouraging but honest. Avoid generic praise.
            - End with a short forward-looking sentence.
            """
            ...

    return EssayEvaluator()
