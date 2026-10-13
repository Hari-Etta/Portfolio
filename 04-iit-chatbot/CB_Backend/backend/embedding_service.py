from __future__ import annotations
"""Embeddings via Google Gemini (free tier).

gemini-embedding-2 (default): task is given as a text prefix, truncated dims are
auto-normalized by the API.
gemini-embedding-001: task is given via task_type; truncated dims are normalized here.

Documents and queries are embedded differently (asymmetric retrieval), so use
embed_document() at ingest time and embed_query() at query time.
"""

from functools import lru_cache
import logging
import math
import time
from typing import List, Optional

from .config import SETTINGS

log = logging.getLogger("embeddings")

_client = None


def _get_client():
    global _client
    if _client is None:
        if not SETTINGS.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        from google import genai

        _client = genai.Client(api_key=SETTINGS.gemini_api_key)
    return _client


def _is_v2() -> bool:
    return SETTINGS.gemini_embed_model.startswith("gemini-embedding-2")


def _normalize(vec: List[float]) -> List[float]:
    n = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / n for x in vec]


def _embed(text: str, *, task_type: str, max_retries: int = 6) -> List[float]:
    from google.genai import types

    cfg = {"output_dimensionality": SETTINGS.embed_dim}
    if not _is_v2():
        cfg["task_type"] = task_type
    delay = 2.0
    for attempt in range(max_retries):
        try:
            resp = _get_client().models.embed_content(
                model=SETTINGS.gemini_embed_model,
                contents=text,
                config=types.EmbedContentConfig(**cfg),
            )
            vec = list(resp.embeddings[0].values)
            return vec if _is_v2() else _normalize(vec)
        except Exception as exc:
            msg = str(exc)
            retryable = any(s in msg for s in ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE", "500"))
            if not retryable or attempt == max_retries - 1:
                raise
            log.warning("embedding rate-limited/unavailable, retrying in %.0fs (%s)", delay, msg[:120])
            time.sleep(delay)
            delay = min(delay * 2, 60)
    raise RuntimeError("unreachable")


def embed_document(text: str, title: Optional[str] = None) -> List[float]:
    if _is_v2():
        return _embed(f"title: {title or 'none'} | text: {text}", task_type="RETRIEVAL_DOCUMENT")
    return _embed(text, task_type="RETRIEVAL_DOCUMENT")


@lru_cache(maxsize=512)
def _embed_query_cached(text: str) -> tuple:
    if _is_v2():
        return tuple(_embed(f"task: search result | query: {text}", task_type="RETRIEVAL_QUERY"))
    return tuple(_embed(text, task_type="RETRIEVAL_QUERY"))


def embed_query(text: str) -> List[float]:
    """Cached: the orchestrator retrieves the same query under several topic filters."""
    return list(_embed_query_cached((text or "").strip()))


# Backwards-compatible name used by older call sites.
embed_text = embed_query
