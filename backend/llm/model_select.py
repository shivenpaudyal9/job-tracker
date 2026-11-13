"""
Pick a Groq chat model that actually exists.

Groq retires models regularly, and a hardcoded model id then fails every
request with 404 model_not_found. This asks the API which models are
available and picks the best match, so a retirement degrades to "a
different model" instead of "no extraction at all".

Set GROQ_MODEL (or GROQ_FAST_MODEL for the small/fast tier) to force one.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_cache: dict[str, str] = {}
_available: Optional[list[str]] = None

# Substrings that mark models which are not general chat models.
_NOT_CHAT = ("whisper", "tts", "guard", "embed", "vision-preview", "playai", "orpheus", "compound", "safeguard")


def _list_models(client) -> list[str]:
    global _available
    if _available is None:
        try:
            _available = [m.id for m in client.models.list().data]
        except Exception as e:
            logger.warning("Could not list Groq models: %s", e)
            return []
    return _available


def _score(model_id: str, fast: bool) -> int:
    m = model_id.lower()
    if any(x in m for x in _NOT_CHAT):
        return -1
    score = 1
    if "llama" in m:
        score += 10
    if "versatile" in m:
        score += 0 if fast else 6
    if "instant" in m:
        score += 6 if fast else 0
    for big in ("70b", "90b", "120b"):
        if big in m:
            score += -2 if fast else 4
    for small in ("8b", "20b", "mini", "small"):
        if small in m:
            score += 4 if fast else -2
    return score


def pick_model(client, preferred: str, fast: bool = False) -> str:
    """Return `preferred` if Groq still serves it, else the best available model."""
    key = f"{preferred}|{fast}"
    if key in _cache:
        return _cache[key]

    forced = os.getenv("GROQ_FAST_MODEL" if fast else "GROQ_MODEL")
    if forced:
        _cache[key] = forced
        return forced

    available = _list_models(client)
    if not available or preferred in available:
        choice = preferred
    else:
        ranked = sorted(available, key=lambda m: (_score(m, fast), m), reverse=True)
        choice = ranked[0] if _score(ranked[0], fast) > 0 else preferred
        logger.warning("Groq model %s is unavailable; using %s instead", preferred, choice)

    _cache[key] = choice
    return choice
