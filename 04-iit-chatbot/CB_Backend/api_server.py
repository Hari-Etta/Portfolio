"""
IIT Chatbot – FastAPI Backend  v2.0
===================================
Free-tier stack: Render (this API) + Neon Postgres (chunks, vectors, feedback)
+ Gemini embeddings + Anthropic Claude (cheapest model) for language tasks.

Abuse/cost guards (protect the Anthropic credits):
- PROXY_SECRET: when set, chat/feedback requests must come through the Next.js proxy.
- RATE_LIMIT_PER_HOUR per client IP, plus DAILY_MESSAGE_CAP across all users.
- GET /api/feedback requires ADMIN_TOKEN (it contains student questions).
"""

from __future__ import annotations

import asyncio
import datetime
import hmac
import json
import logging
import os
import sys
import threading
import time
import uuid
import zoneinfo
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.append(os.path.dirname(__file__))
from backend.config import SETTINGS  # noqa: E402
from backend.db import chunk_count, connection, db_configured, ensure_schema  # noqa: E402
from backend.llm import USAGE, llm_available  # noqa: E402
from backend.orchestrator import chat_turn  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("api")

# ── env ───────────────────────────────────────────────────────────────────────
ALLOWED_ORIGINS: List[str] = [
    o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o.strip()
]
RATE_LIMIT_PER_HOUR: int = int(os.getenv("RATE_LIMIT_PER_HOUR", "30"))
DAILY_MESSAGE_CAP: int = int(os.getenv("DAILY_MESSAGE_CAP", "300"))
PROXY_SECRET: str = os.getenv("PROXY_SECRET", "")
ADMIN_TOKEN: str = os.getenv("ADMIN_TOKEN", "")
# Render sets RENDER_EXTERNAL_URL automatically; keepalive is off everywhere else.
KEEPALIVE_URL: str = os.getenv("KEEPALIVE_URL", os.getenv("RENDER_EXTERNAL_URL", "")).rstrip("/")
KEEPALIVE_SECONDS: int = int(os.getenv("KEEPALIVE_SECONDS", "840"))

_FEEDBACK_FILE = os.path.join(os.path.dirname(__file__), "feedback_log.json")  # local dev only

# ── in-memory counters (reset on restart; fine for a single free instance) ────
_rate_counters: Dict[str, List[float]] = defaultdict(list)
_daily = {"day": "", "count": 0}
_lock = threading.Lock()

INGEST_STATE: Dict[str, Any] = {"status": "not_started", "chunks_indexed": None, "error": None}


# ─────────────────────────────────────────────────────────────────────────────
# Startup: schema + background ingestion + keepalive
# ─────────────────────────────────────────────────────────────────────────────
def _bootstrap_db() -> None:
    if not db_configured():
        INGEST_STATE["status"] = "skipped: DATABASE_URL not set"
        return
    try:
        ensure_schema()
        if not SETTINGS.auto_ingest:
            INGEST_STATE["status"] = "skipped: AUTO_INGEST=false"
            return
        if not SETTINGS.gemini_api_key:
            INGEST_STATE["status"] = "skipped: GEMINI_API_KEY not set"
            return
        INGEST_STATE["status"] = "running"
        from ingest.ingest import ingest

        INGEST_STATE["chunks_indexed"] = ingest()
        INGEST_STATE["status"] = "done"
    except Exception as exc:
        log.exception("startup ingest failed")
        INGEST_STATE.update(status="failed", error=str(exc)[:300])


async def keepalive() -> None:
    """Free Render instances sleep after 15 idle minutes; ping ourselves every 14.
    Hits /api/ping, which never touches the database, so Neon can still scale to zero."""
    await asyncio.sleep(60)
    while True:
        try:
            async with httpx.AsyncClient() as client:
                await client.get(f"{KEEPALIVE_URL}/api/ping", timeout=10)
        except Exception as e:
            log.warning("keepalive ping failed: %s", e)
        await asyncio.sleep(KEEPALIVE_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    threading.Thread(target=_bootstrap_db, name="bootstrap-db", daemon=True).start()
    task = asyncio.create_task(keepalive()) if KEEPALIVE_URL else None
    yield
    if task:
        task.cancel()


app = FastAPI(title="IIT Chatbot API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    query: str
    memory: Optional[Dict[str, Any]] = {}
    conversation_id: Optional[str] = None


class FeedbackRequest(BaseModel):
    conversation_id: str
    message_id: str
    vote: str               # "up" or "down"
    query: str              # the user's question
    bot_answer: str         # the bot response that was rated
    comment: Optional[str] = ""


# ─────────────────────────────────────────────────────────────────────────────
# Guards
# ─────────────────────────────────────────────────────────────────────────────
def _verify_proxy(request: Request) -> bool:
    """True when the request came through our Next.js proxy (or no secret is configured)."""
    if not PROXY_SECRET:
        return True
    got = request.headers.get("x-proxy-secret", "")
    if not hmac.compare_digest(got, PROXY_SECRET):
        raise HTTPException(status_code=403, detail="Forbidden")
    return True


def _client_ip(request: Request) -> str:
    # Only trust the proxy-supplied IP when the proxy authenticated itself.
    if PROXY_SECRET and request.headers.get("x-client-ip"):
        return request.headers["x-client-ip"].strip()
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check_limits(ip: str) -> None:
    now = time.time()
    today = datetime.date.today().isoformat()
    with _lock:
        if _daily["day"] != today:
            _daily.update(day=today, count=0)
        if _daily["count"] >= DAILY_MESSAGE_CAP:
            raise HTTPException(status_code=429, detail="The demo has reached its daily message limit. Please try again tomorrow.")
        _rate_counters[ip] = [t for t in _rate_counters[ip] if now - t < 3600]
        if len(_rate_counters[ip]) >= RATE_LIMIT_PER_HOUR:
            raise HTTPException(status_code=429, detail=f"Rate limit reached – max {RATE_LIMIT_PER_HOUR} messages per hour.")
        _rate_counters[ip].append(now)
        _daily["count"] += 1


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/chat
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/api/chat")
def chat(req: ChatRequest, request: Request):
    _verify_proxy(request)
    _check_limits(_client_ip(request))

    if not req.query or len(req.query) > 2000:
        raise HTTPException(status_code=400, detail="Query must be 1–2000 characters.")

    conversation_id = req.conversation_id or str(uuid.uuid4())
    message_id = str(uuid.uuid4())

    if INGEST_STATE["status"] == "running":
        try:
            ready = chunk_count() > 0
        except Exception:
            ready = False
        if not ready:
            return {
                "answer_markdown": "I'm still loading the IIT policy documents after a fresh deploy. Please try again in a couple of minutes.",
                "mode": "warming_up", "topic": None, "memory": req.memory or {},
                "conversation_id": conversation_id, "message_id": message_id,
            }

    t0 = time.perf_counter()
    try:
        result = chat_turn(req.query, memory=req.memory)
    except Exception:
        log.exception("chat_turn failed conversation_id=%s", conversation_id)
        raise HTTPException(status_code=500, detail="Something went wrong answering that question.")
    log.info(
        "chat ok conversation_id=%s message_id=%s mode=%s intent=%s topic=%s ms=%d",
        conversation_id, message_id, result.get("mode"), result.get("intent"), result.get("topic"),
        (time.perf_counter() - t0) * 1000,
    )
    return {**result, "conversation_id": conversation_id, "message_id": message_id}


# ─────────────────────────────────────────────────────────────────────────────
# Feedback
# ─────────────────────────────────────────────────────────────────────────────
def _write_to_file(entry: Dict[str, Any]) -> None:
    existing: List[Dict] = []
    if os.path.exists(_FEEDBACK_FILE):
        with open(_FEEDBACK_FILE, "r", encoding="utf-8") as f:
            existing = json.load(f)
    existing.append(entry)
    with open(_FEEDBACK_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)


@app.post("/api/feedback")
def feedback(req: FeedbackRequest, request: Request):
    _verify_proxy(request)
    if req.vote not in {"up", "down"}:
        raise HTTPException(status_code=400, detail="vote must be 'up' or 'down'")

    entry: Dict[str, Any] = {
        "timestamp": datetime.datetime.now(zoneinfo.ZoneInfo("America/Chicago")).isoformat(),
        "conversation_id": req.conversation_id,
        "message_id": req.message_id,
        "vote": req.vote,
        "query": req.query[:4000],
        "bot_answer": req.bot_answer[:20000],
        "comment": (req.comment or "")[:4000],
    }

    if not db_configured():
        _write_to_file(entry)
        return {"status": "ok", "saved_to_db": False}

    try:
        with connection() as conn:
            conn.execute(
                """INSERT INTO feedback (timestamp, session_id, query_id, vote, query, bot_answer, feedback_text)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (entry["timestamp"], entry["conversation_id"], entry["message_id"], entry["vote"],
                 entry["query"], entry["bot_answer"], entry["comment"]),
            )
        return {"status": "ok", "saved_to_db": True}
    except Exception as exc:
        log.warning("feedback write failed: %s", exc)
        raise HTTPException(status_code=503, detail="Could not save feedback right now.")


@app.get("/api/feedback")
def get_feedback(request: Request):
    """Admin only: contains student questions. Send header  Authorization: Bearer <ADMIN_TOKEN>."""
    auth = request.headers.get("authorization", "")
    if not ADMIN_TOKEN or not hmac.compare_digest(auth, f"Bearer {ADMIN_TOKEN}"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    with connection() as conn:
        cur = conn.execute("SELECT * FROM feedback ORDER BY timestamp DESC LIMIT 1000")
        cols = [d.name for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


# ─────────────────────────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/api/ping")
def ping():
    """Liveness only. Used by keepalive and Render's health check; never wakes the database."""
    return {"ok": True}


@app.get("/api/health")
def health():
    """Full readiness check (touches Neon, so don't poll it on a schedule)."""
    db_ok, n = False, 0
    try:
        n = chunk_count()
        db_ok = True
    except Exception as exc:
        log.warning("health db check failed: %s", exc)

    ready = db_ok and n > 0 and llm_available() and bool(SETTINGS.gemini_api_key)
    return {
        "status": "ok" if ready else "degraded",
        "database": "ok" if db_ok else ("not configured" if not db_configured() else "unreachable"),
        "document_count": n,
        "ingest": INGEST_STATE,
        "llm": {"provider": SETTINGS.llm_provider,
                "model": SETTINGS.anthropic_model if SETTINGS.llm_provider == "anthropic" else SETTINGS.openai_chat_model,
                "configured": llm_available(), "usage_since_restart": USAGE},
        "embeddings": {"model": SETTINGS.gemini_embed_model, "dim": SETTINGS.embed_dim,
                       "configured": bool(SETTINGS.gemini_api_key)},
        "messages_today": _daily["count"],
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


@app.get("/")
def root():
    return {
        "name": "IIT International Student Chatbot API",
        "version": "2.0.0",
        "endpoints": ["POST /api/chat", "POST /api/feedback", "GET /api/feedback (admin)", "GET /api/health", "GET /api/ping"],
    }
