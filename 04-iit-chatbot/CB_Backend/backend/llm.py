from __future__ import annotations
"""Provider-agnostic LLM calls.

LLM_PROVIDER=anthropic (default) -> Claude (ANTHROPIC_MODEL, default claude-haiku-5-5)
LLM_PROVIDER=openai             -> OpenAI chat completions (OPENAI_CHAT_MODEL)

All callers use llm_json() / llm_text(); nothing else in the codebase knows
which provider is active. If no key is configured, both return empty values and
the orchestrator falls back to its deterministic paths.
"""

from typing import Any, Dict, Optional
import json
import logging
import time

from .config import SETTINGS

log = logging.getLogger("llm")

_client: Any = None

# Rolling token usage for the current process (visible via /api/health).
USAGE: Dict[str, int] = {"calls": 0, "input_tokens": 0, "output_tokens": 0, "errors": 0}


def llm_available() -> bool:
    """True when the configured provider has an API key."""
    if SETTINGS.llm_provider == "anthropic":
        return bool(SETTINGS.anthropic_api_key)
    if SETTINGS.llm_provider == "openai":
        return bool(SETTINGS.openai_api_key)
    return False


def _get_client():
    global _client
    if _client is not None:
        return _client
    if not llm_available():
        return None
    if SETTINGS.llm_provider == "anthropic":
        import anthropic

        _client = anthropic.Anthropic(api_key=SETTINGS.anthropic_api_key, max_retries=2, timeout=60)
    else:
        from openai import OpenAI

        _client = OpenAI(api_key=SETTINGS.openai_api_key)
    return _client


def _complete(system: str, user: str, temperature: float) -> str:
    client = _get_client()
    if client is None:
        return ""

    t0 = time.perf_counter()
    try:
        if SETTINGS.llm_provider == "anthropic":
            # Claude Haiku 5.5 rejects temperature/top_p/prefill; adaptive thinking is on by
            # default, so effort=low keeps latency and cost down for these short tasks.
            resp = client.messages.create(
                model=SETTINGS.anthropic_model,
                max_tokens=SETTINGS.llm_max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_config={"effort": "low"},
            )
            text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
            u = getattr(resp, "usage", None)
            USAGE["input_tokens"] += int(getattr(u, "input_tokens", 0) or 0)
            USAGE["output_tokens"] += int(getattr(u, "output_tokens", 0) or 0)
        else:
            resp = client.chat.completions.create(
                model=SETTINGS.openai_chat_model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            text = resp.choices[0].message.content or ""
            u = getattr(resp, "usage", None)
            USAGE["input_tokens"] += int(getattr(u, "prompt_tokens", 0) or 0)
            USAGE["output_tokens"] += int(getattr(u, "completion_tokens", 0) or 0)
        USAGE["calls"] += 1
        log.info("llm call ok provider=%s ms=%d", SETTINGS.llm_provider, (time.perf_counter() - t0) * 1000)
        return text.strip()
    except Exception as exc:  # never let an LLM outage 500 the chat endpoint
        USAGE["errors"] += 1
        log.warning("llm call failed provider=%s err=%s", SETTINGS.llm_provider, exc)
        return ""


def _parse_json(txt: str) -> Dict[str, Any]:
    txt = (txt or "").strip()
    if txt.startswith("```"):
        txt = txt.strip("`")
        if txt.lower().startswith("json"):
            txt = txt[4:]
    try:
        out = json.loads(txt)
        return out if isinstance(out, dict) else {}
    except Exception:
        start, end = txt.find("{"), txt.rfind("}")
        if start >= 0 and end > start:
            try:
                out = json.loads(txt[start : end + 1])
                return out if isinstance(out, dict) else {}
            except Exception:
                pass
    return {}


def llm_json(*, system: str, user: str, schema_hint: Dict[str, Any], temperature: float = 0.0) -> Dict[str, Any]:
    guidance = (
        "You MUST respond with ONLY valid JSON. No markdown. No extra text. "
        "If unsure, use null values.\n\n"
        f"Schema hint (informal): {json.dumps(schema_hint)}"
    )
    return _parse_json(_complete(system + "\n\n" + guidance, user, temperature))


def llm_text(*, system: str, user: str, temperature: float = 0.2) -> str:
    return _complete(system, user, temperature)
