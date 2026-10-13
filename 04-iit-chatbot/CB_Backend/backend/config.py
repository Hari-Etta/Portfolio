from __future__ import annotations
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _bool(v: str | None, default: bool = False) -> bool:
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    # ── LLM provider ─────────────────────────────────────────────────────────
    # "anthropic" (default) or "openai". Switching is config-only: no code changes.
    llm_provider: str = os.getenv("LLM_PROVIDER", "anthropic").strip().lower()

    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-haiku-5-5")
    llm_max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "2048"))

    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_chat_model: str = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")

    # ── Embeddings (Google Gemini, free tier) ───────────────────────────────
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_embed_model: str = os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-2")
    embed_dim: int = int(os.getenv("EMBED_DIM", "768"))

    # ── LLM feature flags ───────────────────────────────────────────────────
    use_llm_intent: bool = _bool(os.getenv("USE_LLM_INTENT"), True)
    use_llm_slots: bool = _bool(os.getenv("USE_LLM_SLOTS"), True)
    use_llm_narration: bool = _bool(os.getenv("USE_LLM_NARRATION"), True)
    use_llm_answer_synthesis: bool = _bool(os.getenv("USE_LLM_ANSWER_SYNTHESIS"), True)

    policy_rules_path: str = os.getenv(
        "POLICY_RULES_PATH",
        os.path.join(os.path.dirname(__file__), "rules", "policy_rules.yaml"),
    )

    # ── Neon Postgres (chunks + vectors + feedback) ─────────────────────────
    database_url: str = os.getenv("DATABASE_URL", "")
    chunks_table: str = os.getenv("CHUNKS_TABLE", "policy_chunks")
    auto_ingest: bool = _bool(os.getenv("AUTO_INGEST"), True)


SETTINGS = Settings()
