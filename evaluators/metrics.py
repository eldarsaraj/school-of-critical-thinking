"""
Deterministic NLP metrics for essay evaluation.
No LLM calls in this module.
"""
import re
import statistics
from collections import Counter
from pathlib import Path

# ---------------------------------------------------------------------------
# Word-set constants
# ---------------------------------------------------------------------------

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with",
    "by", "from", "up", "about", "into", "over", "after", "i", "me", "my", "myself",
    "we", "our", "you", "your", "he", "him", "his", "she", "her", "it", "its", "they",
    "them", "their", "what", "which", "who", "this", "that", "these", "those", "am",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do",
    "does", "did", "will", "would", "could", "should", "may", "might", "must", "shall",
    "can", "need", "dare", "ought", "used", "to",
}

VAGUE_WORDS = {
    "very", "really", "a lot", "lots", "stuff", "things", "thing", "good", "bad",
    "nice", "great", "awesome", "amazing", "get", "got", "getting", "something",
    "anything", "everything", "nothing", "somehow", "somewhat", "kind of", "sort of",
}

WEAK_VERBS = {
    "be", "am", "is", "are", "was", "were", "been", "being",
    "have", "has", "had", "having",
    "get", "got", "getting",
    "said", "say", "says", "saying",
}

COORDINATING = {"and", "but", "or", "so", "yet", "for", "nor"}
SUBORDINATING = {
    "because", "when", "if", "although", "while", "after", "before", "since",
    "unless", "until", "though", "whereas", "once", "as",
}

# ---------------------------------------------------------------------------
# Brysbaert concreteness norms
# ---------------------------------------------------------------------------

def load_brysbaert_dict(path: str | Path) -> dict[str, float]:
    """Load the Brysbaert et al. (2014) concreteness norms from a TSV file.
    Filters to unigrams (Bigram == 0) with at least 10 ratings (Total >= 10).
    """
    import pandas as pd
    df = pd.read_csv(path, sep="\t")
    d = {}
    for _, row in df.iterrows():
        try:
            if int(row["Bigram"]) == 0 and int(row["Total"]) >= 10:
                word = str(row["Word"]).lower().strip()
                d[word] = float(row["Conc.M"])
        except (ValueError, KeyError):
            continue
    return d


# ---------------------------------------------------------------------------
# Core metric functions
# ---------------------------------------------------------------------------

def _split_sentences(text: str) -> list[str]:
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s for s in sentences if s.strip()]


def basic_counts(text: str) -> dict:
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text.strip()) if p.strip()]
    sentences = _split_sentences(text)
    words = re.findall(r"\b\w+\b", text.lower())
    return {
        "word_count": len(words),
        "sentence_count": len(sentences),
        "paragraph_count": len(paragraphs),
    }


def sentence_length_stats(text: str) -> dict:
    sentences = _split_sentences(text)
    lengths = [len(re.findall(r"\b\w+\b", s)) for s in sentences]
    if not lengths:
        return {"sentence_length_mean": 0.0, "sentence_length_sd": 0.0}
    mean = statistics.mean(lengths)
    sd = statistics.stdev(lengths) if len(lengths) > 1 else 0.0
    return {
        "sentence_length_mean": round(mean, 1),
        "sentence_length_sd": round(sd, 1),
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
    sentences = _split_sentences(text)
    openers = []
    for s in sentences:
        words = re.findall(r"\b\w+\b", s.lower())
        if words:
            openers.append(words[0])
    if not openers:
        return 0.0
    return round(len(set(openers)) / len(openers), 2)


def sentence_type_mix(text: str) -> dict[str, int]:
    sentences = _split_sentences(text)
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
    try:
        from lexical_diversity import lex_div as ld
        tokens = re.findall(r"\b\w+\b", text.lower())
        if len(tokens) < 10:
            return 0.0
        return round(ld.mtld(tokens), 2)
    except Exception:
        return 0.0


def spelling_analysis(text: str) -> dict:
    try:
        from spellchecker import SpellChecker
        spell = SpellChecker()
        words = re.findall(r"\b\w+\b", text.lower())
        if not words:
            return {"spelling_error_rate": 0.0, "spelling_errors": []}
        misspelled = [w for w in spell.unknown(words) if len(w) > 2 and not w.isdigit()]
        rate = round((len(misspelled) / len(words)) * 100, 2)
        return {"spelling_error_rate": rate, "spelling_errors": sorted(misspelled)}
    except Exception:
        return {"spelling_error_rate": 0.0, "spelling_errors": []}


def concreteness_mean(text: str, concreteness_dict: dict) -> float:
    words = re.findall(r"\b\w+\b", text.lower())
    ratings = [concreteness_dict[w] for w in words if w in concreteness_dict]
    if not ratings:
        return 0.0
    return round(sum(ratings) / len(ratings), 2)


def find_weak_transitions(text: str, embedder, threshold: float = 0.35) -> list[str]:
    try:
        import numpy as np
        from sklearn.metrics.pairwise import cosine_similarity
        sentences = _split_sentences(text)
        if len(sentences) < 2:
            return []
        embeddings = embedder.encode(sentences)
        weak = []
        for i in range(len(sentences) - 1):
            sim = cosine_similarity(
                embeddings[i].reshape(1, -1),
                embeddings[i + 1].reshape(1, -1),
            )[0][0]
            if sim < threshold:
                prev = sentences[i][:55] + ("..." if len(sentences[i]) > 55 else "")
                nxt = sentences[i + 1][:55] + ("..." if len(sentences[i + 1]) > 55 else "")
                weak.append(
                    f"Possible abrupt jump (similarity {sim:.2f}): \"{prev}\" → \"{nxt}\""
                )
        return weak
    except Exception:
        return []
