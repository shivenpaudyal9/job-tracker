"""
Local embedding generation using sentence-transformers all-MiniLM-L6-v2.
384-dimensional output. Free, no API calls required.
Model is loaded once and cached for the process lifetime.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_model = None
EMBEDDING_DIM = 384


def _get_model():
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading all-MiniLM-L6-v2 (first load may download ~90MB)...")
            _model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("Embedding model loaded.")
        except ImportError:
            logger.error("sentence-transformers not installed. Run: pip install sentence-transformers")
            raise
    return _model


def embed(text: str) -> Optional[list[float]]:
    if not text or not text.strip():
        return None
    try:
        model = _get_model()
        vector = model.encode(text, normalize_embeddings=True)
        return vector.tolist()
    except Exception as e:
        logger.error("Embedding failed: %s", e)
        return None


def embed_batch(texts: list[str]) -> list[Optional[list[float]]]:
    if not texts:
        return []
    try:
        model = _get_model()
        non_empty = [(i, t) for i, t in enumerate(texts) if t and t.strip()]
        if not non_empty:
            return [None] * len(texts)

        indices, valid_texts = zip(*non_empty)
        vectors = model.encode(list(valid_texts), normalize_embeddings=True, batch_size=32)

        results: list[Optional[list[float]]] = [None] * len(texts)
        for idx, vec in zip(indices, vectors):
            results[idx] = vec.tolist()
        return results
    except Exception as e:
        logger.error("Batch embedding failed: %s", e)
        return [None] * len(texts)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Pure-Python cosine similarity for the non-pgvector fallback path."""
    import math
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)
