"""
Embedding generation via HuggingFace Inference API (no local model loaded).
Falls back to None on rate-limit/error; callers handle gracefully.
"""

import logging
import os
from typing import Optional

import requests
import numpy as np

logger = logging.getLogger(__name__)
EMBEDDING_DIM = 384

_HF_URL = (
    "https://api-inference.huggingface.co"
    "/pipeline/feature-extraction"
    "/sentence-transformers/all-MiniLM-L6-v2"
)
_HF_TOKEN = os.getenv("HF_TOKEN", "")


def embed(text: str) -> Optional[list[float]]:
    """Return a 384-dim embedding via HF Inference API, or None on failure."""
    if not text or not text.strip():
        return None

    headers: dict = {"Authorization": f"Bearer {_HF_TOKEN}"} if _HF_TOKEN else {}
    try:
        resp = requests.post(
            _HF_URL,
            json={"inputs": text[:2048], "options": {"wait_for_model": True}},
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        # HF feature-extraction returns: (1, tokens, 384) or (tokens, 384) or (384,)
        # Mean-pool whatever shape we get down to a 384-dim vector.
        arr = np.array(data, dtype="float32")
        if arr.ndim == 3:
            arr = arr[0]          # (tokens, 384)
        if arr.ndim == 2:
            arr = arr.mean(axis=0)  # (384,)
        if arr.ndim == 1 and len(arr) >= 100:
            return arr.tolist()

        logger.warning("HF embed: unexpected shape %s", arr.shape)
        return None
    except Exception as e:
        logger.warning("HF embed failed (%s): %s", type(e).__name__, e)
        return None


def embed_batch(texts: list[str]) -> list[Optional[list[float]]]:
    """Embed each text individually (HF free tier doesn't batch well)."""
    return [embed(t) for t in texts]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    import math
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)
