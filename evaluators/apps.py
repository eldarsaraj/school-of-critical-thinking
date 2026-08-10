"""
AppConfig for the evaluators app.
Loads the Brysbaert concreteness dict eagerly (it's a local file, fast).
SentenceTransformer and the NOOA evaluator are loaded lazily on first use
so Heroku startup stays fast.
"""
import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)

# Brysbaert dict — populated in ready() from a local TSV (fast)
CONCRETENESS_DICT: dict = {}

# Lazy singletons — initialised on first call to get_embedder() / get_evaluator()
_embedder = None
_evaluator = None


def get_embedder():
    """Return the cached SentenceTransformer, loading it on first call."""
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        logger.info("evaluators: loading SentenceTransformer (first call)…")
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("evaluators: SentenceTransformer ready")
    return _embedder


def get_evaluator():
    """Return the cached NOOA EssayEvaluator, building it on first call."""
    global _evaluator
    if _evaluator is None:
        from django.conf import settings
        nooa_model = getattr(settings, "NOOA_MODEL", "")
        if not nooa_model:
            raise RuntimeError(
                "NOOA_MODEL is not set. "
                "Add it to your environment: e.g. groq/llama-3.3-70b-versatile"
            )
        from nooa.unifiedllm.registry import get_llm_client
        from .agent import build_evaluator
        logger.info("evaluators: building NOOA EssayEvaluator (model=%s)…", nooa_model)
        _evaluator = build_evaluator(get_llm_client(nooa_model))
        logger.info("evaluators: NOOA EssayEvaluator ready")
    return _evaluator


class EvaluatorsConfig(AppConfig):
    name = "evaluators"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        """Load only the local Brysbaert dict at startup. Everything else is lazy."""
        try:
            from django.conf import settings
            from .metrics import load_brysbaert_dict
            import evaluators.apps as _mod
            brysbaert_path = getattr(settings, "BRYSBAERT_PATH", None)
            if brysbaert_path:
                _mod.CONCRETENESS_DICT = load_brysbaert_dict(brysbaert_path)
                logger.info(
                    "evaluators: loaded %d Brysbaert entries from %s",
                    len(_mod.CONCRETENESS_DICT),
                    brysbaert_path,
                )
        except Exception as exc:
            logger.warning("evaluators: could not load Brysbaert dict at startup: %s", exc)
