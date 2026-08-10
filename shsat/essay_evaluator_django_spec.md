# Essay Evaluation Agent — Django Integration Spec

## Goal

Build a production-ready essay evaluation service inside the existing Django project (schoolofcriticalthinking.org) that:

1. Accepts a student essay + prompt (+ optional explicit requirements list).
2. Computes a suite of **deterministic NLP metrics** in pure Python / lightweight libraries.
3. Uses a **NOOA agent** (NVIDIA Object-Oriented Agents) to produce structured feedback and a few higher-level judgments.
4. Returns a validated `EssayEvaluation` object that can be stored and rendered on a student dashboard.

This is the first agent in a larger system that will later also generate standardized-test questions (Hunter College High School and others).

---

## Background / References

- **NOOA paper (required reading for the agent implementer):**  
  https://arxiv.org/pdf/2607.20709

- NOOA turns an ordinary Python class into an AI agent:
  - Class docstring + method docstrings become the LLM prompts.
  - Type annotations become enforceable contracts (via Pydantic).
  - Methods whose body is `...` are agentic (LLM-driven).
  - Ordinary methods stay deterministic Python and can be called by the model (or, as we do here, called *before* the agentic method).

- We use **PredictStrategy** (single-shot structured generation) rather than CodeAct for stability with the current LLM provider.

---

## High-level Architecture (Django)

```
Student submits essay
        │
        ▼
Django view / API endpoint
        │
        ▼
Service layer: compute all deterministic metrics
        │
        ▼
NOOA EssayEvaluator.evaluate(...)   ← only the remaining judgments + feedback
        │
        ▼
Validated EssayEvaluation (Pydantic)
        │
        ▼
Persist (optional) + return JSON / render dashboard
```

**Important design rule already proven in Colab:**  
Compute every reliable metric *outside* the agent and pass the values in as arguments. Do **not** ask the LLM to invent word counts, MTLD, concreteness, spelling errors, etc.

---

## Dependencies to add

```txt
nooa
pydantic
lexical-diversity
pyspellchecker
sentence-transformers
scikit-learn
pandas
requests
# optional later: language-tool-python  (when self-hosted LanguageTool is ready)
```

LLM provider: currently Groq (`groq/llama-3.3-70b-versatile`) via LiteLLM inside NOOA. Make the model string configurable via Django settings / environment variable.

---

## Core Data Contract — `EssayEvaluation`

```python
from pydantic import BaseModel, Field
from typing import List, Dict

class EssayEvaluation(BaseModel):
    # --- Basic counts ---
    word_count: int
    sentence_count: int
    paragraph_count: int

    # --- Lexical ---
    mtld: float = Field(..., description="Lexical diversity (MTLD). Higher = more varied vocabulary.")
    vague_word_density: float = Field(..., description="Proportion of vague words.")
    weak_verb_rate: float = Field(..., description="Share of weak verbs.")
    top_repeated_words: List[str] = Field(..., description="Most repeated content words (excluding stop words).")
    concreteness_mean: float = Field(..., description="Average concreteness (Brysbaert 1–5 scale).")

    # --- Sentence structure ---
    sentence_length_mean: float
    sentence_length_sd: float = Field(..., description="Standard deviation of sentence lengths.")
    sentence_opener_variety: float = Field(..., description="Variety of sentence openings (0–1).")
    sentence_type_mix: Dict[str, int] = Field(..., description="Counts of simple/compound/complex sentences.")

    # --- Organization ---
    sentences_per_paragraph_mean: float
    weak_transitions: List[str] = Field(..., description="Descriptions of the weakest sentence-to-sentence transitions.")

    # --- Development / Prompt coverage ---
    on_prompt_relevance: float = Field(..., description="0–1 how on-topic the essay is.")
    prompt_coverage: Dict[str, float] = Field(..., description="Requirement text → coverage score 0–1.")

    # --- Mechanics ---
    spelling_error_rate: float = Field(..., description="Spelling errors per 100 words.")
    spelling_errors: List[str] = Field(..., description="List of misspelled words found.")
    grammar_flags: List[str] = Field(default_factory=list, description="Human-readable grammar/punctuation issues. Empty until LanguageTool is wired.")

    # --- LLM-generated part ---
    feedback: str = Field(..., description="Short, constructive natural-language feedback for the student.")
```

This model is the single source of truth for both the agent return type and the API response / database serialization.

---

## Deterministic Metric Functions (copy almost verbatim)

These must live in a pure-Python module (e.g. `evaluators/metrics.py`) and must **not** call the LLM.

### Constants

```python
STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with",
    "by", "from", "up", "about", "into", "over", "after", "i", "me", "my", "myself",
    "we", "our", "you", "your", "he", "him", "his", "she", "her", "it", "its", "they",
    "them", "their", "what", "which", "who", "this", "that", "these", "those", "am",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do",
    "does", "did", "will", "would", "could", "should", "may", "might", "must", "shall",
    "can", "need", "dare", "ought", "used", "to"
}

VAGUE_WORDS = {
    "very", "really", "a lot", "lots", "stuff", "things", "thing", "good", "bad",
    "nice", "great", "awesome", "amazing", "get", "got", "getting", "something",
    "anything", "everything", "nothing", "somehow", "somewhat", "kind of", "sort of"
}

WEAK_VERBS = {
    "be", "am", "is", "are", "was", "were", "been", "being",
    "have", "has", "had", "having",
    "get", "got", "getting",
    "said", "say", "says", "saying"
}

COORDINATING = {"and", "but", "or", "so", "yet", "for", "nor"}
SUBORDINATING = {
    "because", "when", "if", "although", "while", "after", "before", "since",
    "unless", "until", "though", "whereas", "once", "as"
}
```

### Core functions

```python
import re
import statistics
from collections import Counter
from lexical_diversity import lex_div as ld
from spellchecker import SpellChecker

spell = SpellChecker()

def basic_counts(text: str) -> dict:
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text.strip()) if p.strip()]
    paragraph_count = len(paragraphs)
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    sentences = [s for s in sentences if s.strip()]
    sentence_count = len(sentences)
    words = re.findall(r"\b\w+\b", text.lower())
    word_count = len(words)
    return {
        "word_count": word_count,
        "sentence_count": sentence_count,
        "paragraph_count": paragraph_count
    }

def sentence_length_stats(text: str) -> dict:
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    sentences = [s for s in sentences if s.strip()]
    lengths = [len(re.findall(r"\b\w+\b", s)) for s in sentences]
    if not lengths:
        return {"sentence_length_mean": 0.0, "sentence_length_sd": 0.0}
    mean = statistics.mean(lengths)
    sd = statistics.stdev(lengths) if len(lengths) > 1 else 0.0
    return {
        "sentence_length_mean": round(mean, 1),
        "sentence_length_sd": round(sd, 1)
    }

def top_repeated_content_words(text: str, n: int = 5) -> list[str]:
    words = re.findall(r"\b\w+\b", text.lower())
    content_words = [w for w in words if w not in STOPWORDS and len(w) > 2]
    counts = Counter(content_words)
    return [word for word, freq in counts.most_common(n) if freq > 1]

def vague_word_density(text: str) -> float:
    words = re.findall(r"\b\w+\b", text.lower())
    if not words:
        return 0.0
    return round(sum(1 for w in words if w in VAGUE_WORDS) / len(words), 3)

def weak_verb_rate(text: str) -> float:
    words = re.findall(r"\b\w+\b", text.lower())
    if not words:
        return 0.0
    return round(sum(1 for w in words if w in WEAK_VERBS) / len(words), 3)

def sentence_opener_variety(text: str) -> float:
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    sentences = [s for s in sentences if s.strip()]
    if not sentences:
        return 0.0
    openers = []
    for s in sentences:
        words = re.findall(r"\b\w+\b", s.lower())
        if words:
            openers.append(words[0])
    if not openers:
        return 0.0
    return round(len(set(openers)) / len(openers), 2)

def sentence_type_mix(text: str) -> dict[str, int]:
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    sentences = [s for s in sentences if s.strip()]
    mix = {"simple": 0, "compound": 0, "complex": 0}
    for s in sentences:
        words = set(re.findall(r"\b\w+\b", s.lower()))
        if words & SUBORDINATING:
            mix["complex"] += 1
        elif words & COORDINATING:
            mix["compound"] += 1
        else:
            mix["simple"] += 1
    return mix

def compute_mtld(text: str) -> float:
    tokens = re.findall(r"\b\w+\b", text.lower())
    if len(tokens) < 10:
        return 0.0
    return round(ld.mtld(tokens), 2)

def spelling_analysis(text: str) -> dict:
    words = re.findall(r"\b\w+\b", text.lower())
    if not words:
        return {"spelling_error_rate": 0.0, "spelling_errors": []}
    misspelled = [w for w in spell.unknown(words) if len(w) > 2 and not w.isdigit()]
    rate = round((len(misspelled) / len(words)) * 100, 2)
    return {
        "spelling_error_rate": rate,
        "spelling_errors": sorted(misspelled)
    }
```

### Concreteness (full Brysbaert norms)

Load once at startup (AppConfig.ready or a module-level cache):

```python
# Source: Brysbaert, Warriner & Kuperman (2014)
# https://github.com/ArtsEngine/concreteness
# Scale: 1 = very abstract → 5 = very concrete

import pandas as pd
from pathlib import Path

def load_brysbaert_dict(path: str | Path) -> dict[str, float]:
    df = pd.read_csv(path, sep="\t")
    d = {}
    for _, row in df.iterrows():
        if row["Bigram"] == 0 and row["Total"] >= 10:
            word = str(row["Word"]).lower().strip()
            d[word] = float(row["Conc.M"])
    return d

# In production ship the file under data/brysbaert_concreteness.tsv
# and load it once:
# CONCRETENESS = load_brysbaert_dict(settings.BRYSBAERT_PATH)

def concreteness_mean(text: str, concreteness_dict: dict) -> float:
    words = re.findall(r"\b\w+\b", text.lower())
    ratings = [concreteness_dict[w] for w in words if w in concreteness_dict]
    if not ratings:
        return 0.0
    return round(sum(ratings) / len(ratings), 2)
```

### Weak transitions (sentence embeddings)

```python
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Load once at startup
# embedder = SentenceTransformer("all-MiniLM-L6-v2")

def find_weak_transitions(text: str, embedder, threshold: float = 0.35) -> list[str]:
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]
    if len(sentences) < 2:
        return []
    embeddings = embedder.encode(sentences)
    weak = []
    for i in range(len(sentences) - 1):
        sim = cosine_similarity(
            embeddings[i].reshape(1, -1),
            embeddings[i + 1].reshape(1, -1)
        )[0][0]
        if sim < threshold:
            prev = sentences[i][:55] + ("..." if len(sentences[i]) > 55 else "")
            nxt  = sentences[i + 1][:55] + ("..." if len(sentences[i + 1]) > 55 else "")
            weak.append(f"Possible abrupt jump (similarity {sim:.2f}): \"{prev}\" → \"{nxt}\"")
    return weak
```

---

## The NOOA Agent

```python
from nooa import Agent, strategy
from nooa.strategies import PredictStrategy
from nooa.unifiedllm.registry import get_llm_client

# llm = get_llm_client(settings.NOOA_MODEL)   # e.g. "groq/llama-3.3-70b-versatile"

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
        - Keep the tone encouraging but honest. Avoid generic praise.
        - End with a short forward-looking sentence.
        """
        ...
```

---

## Service-layer orchestration (what the Django view should call)

```python
async def evaluate_essay(
    essay: str,
    prompt: str,
    requirements: list[str] | None = None,
) -> EssayEvaluation:
    """Compute metrics then call the NOOA agent. Returns a validated EssayEvaluation."""

    if requirements is None:
        # Fallback: treat the whole prompt as a single requirement, or parse it.
        requirements = [prompt.strip()]

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
    conc = concreteness_mean(essay, CONCRETENESS)
    transitions = find_weak_transitions(essay, embedder)

    agent = EssayEvaluator()
    result = await agent.evaluate(
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
```

**Critical:** Always recompute every metric on the *current* essay text. Never reuse values from a previous evaluation.

---

## Django integration checklist

1. **App structure suggestion**
   ```
   evaluators/
       __init__.py
       metrics.py          # all deterministic functions
       agent.py            # EssayEvaluator + EssayEvaluation
       services.py         # evaluate_essay() orchestration
       apps.py             # load Brysbaert + embedder on ready()
   ```

2. **Settings**
   - `NOOA_MODEL = "groq/llama-3.3-70b-versatile"` (or env)
   - `GROQ_API_KEY` (or whatever provider) via environment / secrets
   - `BRYSBAERT_PATH = BASE_DIR / "data" / "brysbaert_concreteness.tsv"`

3. **Startup loading** (in `AppConfig.ready`):
   - Load Brysbaert dictionary once.
   - Load `SentenceTransformer("all-MiniLM-L6-v2")` once (or lazy-load on first use and cache).

4. **API / view**
   - Accept POST with `essay`, `prompt`, optional `requirements` (list of strings).
   - Call `await evaluate_essay(...)`.
   - Return `result.model_dump()` as JSON.
   - Optionally persist the full evaluation against a StudentEssay model.

5. **Grammar flags (deferred)**
   - Keep `grammar_flags: list[str] = []` for now.
   - Later: self-host LanguageTool (Docker) and call it from a pure function that returns a list of human-readable messages. Do **not** ask the LLM to invent grammar issues.

6. **Async**
   - The agent method is `async`. Use Django async views or `async_to_sync` carefully. Prefer native async if the project already supports it.

7. **Error handling**
   - Catch LLM / network failures and return a clear error to the frontend.
   - Never let a failed LLM call crash the request without a user-visible message.

---

## Feedback quality requirements (already tuned)

The agent docstring above encodes the product requirements:

- Written for middle-school students preparing for the **Hunter College High School** entrance essay.
- Must reference concrete metrics (especially low coverage items and weak transitions).
- One specific strength + one actionable improvement.
- No generic “Great job!” praise.

When testing, use essays of clearly different quality. The pipeline should produce:

- Higher concreteness, higher prompt_coverage, fewer weak transitions → stronger feedback.
- Low concreteness, low “Use specific details” score, high vague-word rate → feedback that tells the student to add concrete sensory detail.

---

## Out of scope for this first ticket

- Full LanguageTool grammar service (design only; leave the field empty).
- Question-generation agents.
- Frontend dashboard visualization (the API just needs to return the full structured object).
- Multi-language support.

---

## Acceptance criteria

- [ ] `evaluate_essay(essay, prompt, requirements)` returns a valid `EssayEvaluation`.
- [ ] All numeric metrics listed above are computed deterministically and match independent recalculation.
- [ ] `prompt_coverage` keys are exactly the strings passed in `requirements`.
- [ ] `feedback` is 4–6 sentences, specific, and references at least one metric or coverage score.
- [ ] Brysbaert dictionary and embedding model are loaded once, not per request.
- [ ] No LLM call is made for word count, MTLD, spelling, concreteness, or transition detection.
- [ ] API endpoint (or internal service) is callable from the existing Django project without breaking current pages.

---

## Reference implementation notes (from Colab prototype)

- PredictStrategy is more stable than CodeAct with the current Groq model for large structured outputs.
- Always pass already-computed metrics as arguments; do not rely on the model calling ordinary methods.
- Short, explicit requirements lists produce far more consistent `prompt_coverage` than asking the model to invent the keys.
- The full Brysbaert file (~37k lemmas) is required for production; a tiny hand-curated dict is unacceptable.

---

## Paper

NVIDIA Object-Oriented Agents (NOOA):  
https://arxiv.org/pdf/2607.20709

Implement the above faithfully. Prefer clarity and reliability over premature optimization.
