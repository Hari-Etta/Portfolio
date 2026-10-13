# CB_Backend — FastAPI orchestrator

A policy-grounded chatbot for IIT international student questions (CPT, OPT, STEM OPT, F-1 status, RCL, travel, SSN, insurance).

## How a question is handled (`backend/orchestrator.py`)

1. Out-of-scope check (regex) → refuse
2. Smalltalk / help
3. Intent + topic detection (`intent.py`, `topic.py`)
4. Disambiguation (`ambiguity.py`, e.g. on-campus vs CPT vs OPT hours)
5. Eligibility questions → slot filling (`slot_filling.py`) + deterministic YAML rule engine (`rule_engine.py`, `rules/policy_rules.yaml`). The LLM never decides eligibility.
6. Hybrid retrieval (`retrieval.py`):
   - Postgres full-text search and pgvector cosine search run in one round trip to Neon
   - The two lists are merged with Reciprocal Rank Fusion
   - A topic-aware reranker reorders the merged list
7. Answer synthesis (`answer_synth.py`):
   - Claude writes the answer using only the retrieved policy text
   - Deterministic templates handle timing, document, contact and similar questions
8. Response with source citations

## Providers (all switchable by env var; see `.env.example`)

| Concern | Default | Module |
|---|---|---|
| LLM | Anthropic `claude-haiku-5-5` (`LLM_PROVIDER=openai` also supported) | `backend/llm.py` |
| Embeddings | Google `gemini-embedding-2`, 768 dims | `backend/embedding_service.py` |
| Store / search | Neon Postgres + pgvector + `tsvector` | `backend/db.py`, `backend/retrieval.py` |

## Ingestion (`ingest/`)

- Source pages live in `data/md/**/*.md`.
- They are split by a section-aware chunker (`chunking.py`), embedded, and upserted into Postgres.
- Per-file sha256 hashes in the `ingest_manifest` table mean only changed files are re-embedded.
- The API runs ingestion in the background on startup (`AUTO_INGEST=true`). You can also run it manually with `python -m ingest.ingest [--force]`.

## API

| Method | Path | Notes |
|---|---|---|
| POST | `/api/chat` | Requires `X-Proxy-Secret` when `PROXY_SECRET` is set. Limited to `RATE_LIMIT_PER_HOUR` per client IP and `DAILY_MESSAGE_CAP` across all users |
| POST | `/api/feedback` | Up/down vote and comment, stored in Neon |
| GET | `/api/feedback` | Admin only (`Authorization: Bearer $ADMIN_TOKEN`) |
| GET | `/api/health` | Readiness: DB, chunk count, ingest status, LLM token usage |
| GET | `/api/ping` | Liveness, used by keepalive and Render's health check |

Deployment steps: see [`../DEPLOY.md`](../DEPLOY.md).

> Not legal advice. For official determinations, students should contact the IIT Office of Global Services.
