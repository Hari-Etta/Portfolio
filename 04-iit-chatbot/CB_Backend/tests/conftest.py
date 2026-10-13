"""Test setup: runs fully offline.

- Needs a Postgres with pgvector at TEST_DATABASE_URL (docker compose up -d works).
  DB tests are skipped if it isn't set.
- Gemini and Claude are replaced with deterministic fakes, so no keys or credits are used.
"""
import hashlib
import math
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TEST_DB = os.getenv("TEST_DATABASE_URL", "")
os.environ.update({
    "DATABASE_URL": TEST_DB,
    "CHUNKS_TABLE": "test_policy_chunks",
    "GEMINI_API_KEY": "fake",
    "ANTHROPIC_API_KEY": "",   # LLM off -> deterministic orchestrator paths
    "AUTO_INGEST": "false",
    "EMBED_DIM": "768",
    "PROXY_SECRET": "test-proxy-secret",
    "ADMIN_TOKEN": "test-admin-token",
    "RATE_LIMIT_PER_HOUR": "3",
    "DAILY_MESSAGE_CAP": "1000",
    "KEEPALIVE_URL": "",
    "RENDER_EXTERNAL_URL": "",
})

import pytest  # noqa: E402

_WORD = re.compile(r"[a-z0-9]+")


def fake_embed(text: str, dim: int = 768):
    """Hashed bag-of-words vector: similar wording -> similar vectors. Deterministic, offline."""
    v = [0.0] * dim
    for w in _WORD.findall((text or "").lower()):
        h = int(hashlib.md5(w.encode()).hexdigest(), 16)
        v[h % dim] += 1.0 if (h >> 20) % 2 else -1.0
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


class _WsEncoding:
    """Stand-in for tiktoken (its BPE file is downloaded at runtime, which tests avoid)."""
    def encode(self, text):
        return (text or "").split()

    def decode(self, toks):
        return " ".join(toks)


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    import backend.embedding_service as es
    import backend.retrieval as r
    import ingest.ingest as ing

    es._embed_query_cached.cache_clear()
    monkeypatch.setattr(r, "embed_query", lambda t: fake_embed(t))
    monkeypatch.setattr(ing, "embed_document", lambda t, title=None: fake_embed(t))
    yield


def pytest_configure(config):
    try:
        import tiktoken
        tiktoken.get_encoding("cl100k_base")
    except Exception:
        import types
        sys.modules["tiktoken"] = types.SimpleNamespace(get_encoding=lambda name: _WsEncoding())


requires_db = pytest.mark.skipif(not TEST_DB, reason="TEST_DATABASE_URL not set")
