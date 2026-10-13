from __future__ import annotations
"""Ingestion: Markdown policy pages -> section-aware chunks -> Gemini embeddings -> Neon Postgres.

Run manually:   python -m ingest.ingest            (only changed files)
                python -m ingest.ingest --force    (re-embed everything)
The API server also calls ingest() in the background on startup when AUTO_INGEST=true,
so a fresh Neon database fills itself on the first Render deploy.

Change detection uses the ingest_manifest table (sha256 per file + embedding model/dim),
so it is safe to run repeatedly; unchanged files cost nothing.
"""

import argparse
import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List

from backend.config import SETTINGS
from backend.db import connection, ensure_schema
from backend.embedding_service import embed_document
from ingest.md_parser import read_md, parse_metadata
from ingest.chunking import make_chunks

log = logging.getLogger("ingest")

DATA_ROOT = Path(__file__).resolve().parents[1] / "data"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8192), b""):
            h.update(block)
    return h.hexdigest()


def iter_md_files() -> List[Path]:
    return sorted(p for p in DATA_ROOT.rglob("*.md"))


def _load_manifest() -> Dict[str, Dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute("SELECT rel_path, sha256, embedding_model, embed_dim FROM ingest_manifest").fetchall()
    return {r[0]: {"sha256": r[1], "embedding_model": r[2], "embed_dim": r[3]} for r in rows}


def ingest(force: bool = False) -> int:
    """Returns the number of chunks (re)indexed."""
    ensure_schema()
    table = SETTINGS.chunks_table
    manifest = {} if force else _load_manifest()

    md_files = iter_md_files()
    if not md_files:
        raise RuntimeError(f"No .md files found under {DATA_ROOT}")

    total = 0
    for path in md_files:
        # Relative, forward-slash path: chunk ids stay identical across machines (laptop vs Render).
        rel = path.relative_to(DATA_ROOT).as_posix()
        file_hash = sha256_file(path)
        prev = manifest.get(rel)
        if prev and prev["sha256"] == file_hash and prev["embedding_model"] == SETTINGS.gemini_embed_model \
                and int(prev["embed_dim"]) == SETTINGS.embed_dim:
            continue

        md_text = read_md(path)
        meta = parse_metadata(md_text, fallback_category=path.parent.name, fallback_doc_id=path.stem)
        policy_version = meta.last_checked or file_hash[:10]
        chunks = make_chunks(
            md_text=md_text,
            category=meta.category,
            policy_topic=meta.doc_id,  # Doc_ID is the stable topic key
            doc_title=meta.title,
            source_file=rel,
            source_url=meta.source_url,
            policy_version=policy_version,
        )

        # Embed first (slow, network), then write the whole file atomically.
        rows = []
        for ch in chunks:
            vec = embed_document(ch.text, title=ch.doc_title)
            rows.append((
                ch.chunk_id, ch.text, ch.heading, ch.category, ch.policy_topic, ch.doc_title,
                ch.section_title, ch.section_path, ch.heading_level, ch.source_file,
                ch.source_url, ch.policy_version, "[" + ",".join(f"{x:.7f}" for x in vec) + "]",
            ))

        with connection() as conn:
            with conn.transaction():
                # Drop this file's old chunks so edited pages don't leave stale text behind.
                conn.execute(f"DELETE FROM {table} WHERE source_file = %s", (rel,))
                with conn.cursor() as cur:
                    cur.executemany(
                        f"""INSERT INTO {table}
                            (chunk_id, text, heading, category, policy_topic, doc_title, section_title,
                             section_path, heading_level, source_file, source_url, policy_version, embedding)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::vector)
                            ON CONFLICT (chunk_id) DO UPDATE SET
                              text = EXCLUDED.text, heading = EXCLUDED.heading, category = EXCLUDED.category,
                              policy_topic = EXCLUDED.policy_topic, doc_title = EXCLUDED.doc_title,
                              section_title = EXCLUDED.section_title, section_path = EXCLUDED.section_path,
                              heading_level = EXCLUDED.heading_level, source_file = EXCLUDED.source_file,
                              source_url = EXCLUDED.source_url, policy_version = EXCLUDED.policy_version,
                              embedding = EXCLUDED.embedding, indexed_at = now()""",
                        rows,
                    )
                conn.execute(
                    """INSERT INTO ingest_manifest (rel_path, sha256, chunks, embedding_model, embed_dim, doc_id, source_url, indexed_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s, now())
                       ON CONFLICT (rel_path) DO UPDATE SET sha256 = EXCLUDED.sha256, chunks = EXCLUDED.chunks,
                         embedding_model = EXCLUDED.embedding_model, embed_dim = EXCLUDED.embed_dim,
                         doc_id = EXCLUDED.doc_id, source_url = EXCLUDED.source_url, indexed_at = now()""",
                    (rel, file_hash, len(chunks), SETTINGS.gemini_embed_model, SETTINGS.embed_dim,
                     meta.doc_id, meta.source_url),
                )
        total += len(chunks)
        log.info("indexed %d chunks from %s", len(chunks), rel)
        print(f"Indexed {len(chunks)} chunks from {rel}", flush=True)

    # Remove chunks for Markdown files that no longer exist.
    current = {p.relative_to(DATA_ROOT).as_posix() for p in md_files}
    with connection() as conn:
        known = [r[0] for r in conn.execute("SELECT rel_path FROM ingest_manifest").fetchall()]
        for rel in known:
            if rel not in current:
                conn.execute(f"DELETE FROM {table} WHERE source_file = %s", (rel,))
                conn.execute("DELETE FROM ingest_manifest WHERE rel_path = %s", (rel,))
                print(f"Removed chunks for deleted file {rel}", flush=True)

    print(f"Done. {total} chunks (re)indexed." if total else "No changes detected. Nothing to index.", flush=True)
    return total


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="re-embed and re-index every file")
    ingest(force=ap.parse_args().force)
