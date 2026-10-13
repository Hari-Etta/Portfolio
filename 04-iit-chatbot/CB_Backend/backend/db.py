from __future__ import annotations
"""Neon Postgres access: one small connection pool shared by retrieval, ingest and feedback.

Neon free tier notes:
- Computes auto-suspend after 5 idle minutes. The pool keeps no idle connections
  (min_size=0, max_idle=120s) so it never holds the compute awake.
- Works with both the direct and the "-pooler" (PgBouncer) connection string;
  prepared statements are disabled for PgBouncer compatibility.
"""

from contextlib import contextmanager
import logging
from typing import Iterator, Optional

from .config import SETTINGS

log = logging.getLogger("db")

_pool = None


def db_configured() -> bool:
    return bool(SETTINGS.database_url)


def _configure(conn) -> None:
    conn.prepare_threshold = None


def get_pool():
    global _pool
    if _pool is None:
        if not db_configured():
            raise RuntimeError("DATABASE_URL is not set")
        from psycopg_pool import ConnectionPool

        _pool = ConnectionPool(
            SETTINGS.database_url,
            min_size=0,
            max_size=4,
            max_idle=120,
            timeout=30,
            kwargs={"autocommit": True},
            configure=_configure,
            check=ConnectionPool.check_connection,
            open=True,
        )
    return _pool


@contextmanager
def connection() -> Iterator["psycopg.Connection"]:  # noqa: F821
    with get_pool().connection() as conn:
        yield conn


def schema_sql(table: Optional[str] = None, dim: Optional[int] = None) -> str:
    t = table or SETTINGS.chunks_table
    d = int(dim or SETTINGS.embed_dim)
    return f"""
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS {t} (
    chunk_id        TEXT PRIMARY KEY,
    text            TEXT NOT NULL,
    heading         TEXT,
    category        TEXT,
    policy_topic    TEXT,
    doc_title       TEXT,
    section_title   TEXT,
    section_path    TEXT,
    heading_level   INTEGER,
    source_file     TEXT,
    source_url      TEXT,
    policy_version  TEXT,
    indexed_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    embedding       vector({d}),
    -- Field weights mirror the old Elasticsearch boosts: body text (A) > headings/titles (B) > topic key (C)
    fts tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(text, '')), 'A') ||
        setweight(to_tsvector('english',
            coalesce(heading, '') || ' ' || coalesce(section_title, '') || ' ' ||
            coalesce(section_path, '') || ' ' || coalesce(doc_title, '')), 'B') ||
        setweight(to_tsvector('english', replace(coalesce(policy_topic, ''), '_', ' ')), 'C')
    ) STORED
);
CREATE INDEX IF NOT EXISTS {t}_fts_idx   ON {t} USING GIN (fts);
CREATE INDEX IF NOT EXISTS {t}_topic_idx ON {t} (policy_topic);
CREATE INDEX IF NOT EXISTS {t}_cat_idx   ON {t} (category);
-- No ANN index on purpose: at a few hundred rows an exact cosine scan is fast and has perfect recall.

CREATE TABLE IF NOT EXISTS ingest_manifest (
    rel_path        TEXT PRIMARY KEY,
    sha256          TEXT NOT NULL,
    chunks          INTEGER NOT NULL,
    embedding_model TEXT NOT NULL,
    embed_dim       INTEGER NOT NULL,
    doc_id          TEXT,
    source_url      TEXT,
    indexed_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS feedback (
    id             BIGSERIAL PRIMARY KEY,
    timestamp      TIMESTAMPTZ NOT NULL DEFAULT now(),
    session_id     TEXT,
    query_id       TEXT,
    vote           TEXT NOT NULL CHECK (vote IN ('up', 'down')),
    query          TEXT,
    bot_answer     TEXT,
    feedback_text  TEXT
);
"""


def ensure_schema() -> None:
    with connection() as conn:
        conn.execute(schema_sql())


def chunk_count() -> int:
    with connection() as conn:
        row = conn.execute(f"SELECT count(*) FROM {SETTINGS.chunks_table}").fetchone()
        return int(row[0]) if row else 0
