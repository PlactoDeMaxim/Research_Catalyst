"""
Unified LLM client for the Code Mapper module.

This client supports Ollama Cloud models via `POST https://ollama.com/api/chat`.
It preserves the existing `chat()` / `chat_json()` behavior by mapping Ollama
responses into an OpenAI-like shape.
"""

from __future__ import annotations

import json
import logging
import os
import collections
import time
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration (environment variables)
# ---------------------------------------------------------------------------


def _settings() -> dict[str, Any]:
    """Read runtime settings from environment.

    This is evaluated per-request so changed env vars take effect after restart
    without requiring module reload ordering assumptions.
    """
    return {
        # Ollama Cloud
        # Docs:
        # - https://ollama.com/api/chat (base URL: https://ollama.com)
        "api_key": os.getenv("OLLAMA_API_KEY", "").strip(),
        "base_url": os.getenv("OLLAMA_BASE_URL", "https://ollama.com").strip(),
        "model": _normalize_model_id(
            # Prefer explicit Ollama Cloud model tag.
            # Do NOT fall back to `LLM_MODEL` because in this repo `LLM_MODEL`
            # is often an OpenRouter slug (which would break Ollama).
            os.getenv("OLLAMA_MODEL", "gpt-oss:120b-cloud").strip()
        ),
        "temperature": float(os.getenv("LLM_TEMPERATURE", "0.3")),
        "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "4096")),
        "timeout": int(os.getenv("LLM_TIMEOUT", "120")),
        "max_retries": int(os.getenv("LLM_MAX_RETRIES", "3")),
    }


def _normalize_model_id(model_id: str) -> str:
    """Map known legacy aliases/slugs to current OpenRouter model IDs."""
    if not model_id:
        return model_id
    aliases = {
        # Legacy/incorrect Nemotron slug seen in local config.
        "nvidia/llama-3.1-nemotron-70b-instruct:free": "nvidia/nemotron-3-super-120b-a12b:free",
        # Common shorthand users paste from old examples.
        "nvidia/nemotron-3-super:free": "nvidia/nemotron-3-super-120b-a12b:free",
    }
    return aliases.get(model_id, model_id)

# ---------------------------------------------------------------------------
# Token / cost tracking (in-memory, per-process)
# ---------------------------------------------------------------------------

_usage_log: list[dict[str, Any]] = []


def get_usage_summary() -> dict[str, Any]:
    total_prompt = sum(u.get("prompt_tokens", 0) for u in _usage_log)
    total_completion = sum(u.get("completion_tokens", 0) for u in _usage_log)
    return {
        "total_calls": len(_usage_log),
        "total_prompt_tokens": total_prompt,
        "total_completion_tokens": total_completion,
        "total_tokens": total_prompt + total_completion,
    }


# ---------------------------------------------------------------------------
# LLM strict rate limiting (process-local)
# ---------------------------------------------------------------------------

_LLM_RATE_LOCK = __import__("asyncio").Lock()
_LLM_CALL_TS: collections.deque[float] = collections.deque()
_LLM_LAST_CALL_AT: float = 0.0

_LLM_MIN_INTERVAL_SECONDS = 1.0
_LLM_MAX_PER_MINUTE = 40

async def _wait_llm_slot() -> None:
    """Enforce: 1 request/sec and 40 requests/min for LLM calls."""
    import asyncio
    global _LLM_LAST_CALL_AT

    while True:
        async with _LLM_RATE_LOCK:
            now = time.monotonic()

            # Drop timestamps older than 60 seconds.
            while _LLM_CALL_TS and now - _LLM_CALL_TS[0] >= 60.0:
                _LLM_CALL_TS.popleft()

            wait_1 = max(
                0.0,
                _LLM_MIN_INTERVAL_SECONDS - (now - _LLM_LAST_CALL_AT),
            )

            wait_min = 0.0
            if len(_LLM_CALL_TS) >= _LLM_MAX_PER_MINUTE:
                oldest = _LLM_CALL_TS[0]
                wait_min = max(0.0, 60.0 - (now - oldest))

            wait_for = max(wait_1, wait_min)
            if wait_for <= 0.0:
                _LLM_LAST_CALL_AT = now
                _LLM_CALL_TS.append(now)
                return

        await asyncio.sleep(wait_for)


# ---------------------------------------------------------------------------
# Core async helpers
# ---------------------------------------------------------------------------

async def _post_chat(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    response_format: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Low-level POST to the Ollama chat endpoint with retries.

    Returns an OpenAI-like response payload:
      { "choices": [ { "message": { "content": "..." } } ] , ... }
    """
    cfg = _settings()
    if not cfg["api_key"]:
        raise RuntimeError(
            "OLLAMA_API_KEY is missing. Set it in backend/.env and restart FastAPI."
        )

    url = f"{cfg['base_url'].rstrip('/')}/api/chat"
    headers = {
        "Authorization": f"Bearer {cfg['api_key']}",
        "Content-Type": "application/json",
    }

    payload: dict[str, Any] = {
        "model": model or cfg["model"],
        "messages": messages,
        # Non-streaming: we want a single JSON response for simplicity.
        "stream": False,
    }
    payload["options"] = {
        "temperature": temperature if temperature is not None else cfg["temperature"],
        # Ollama uses `num_predict` for max output tokens.
        "num_predict": max_tokens if max_tokens is not None else cfg["max_tokens"],
    }

    # Map our generic `response_format` concept to Ollama's `format`.
    # - chat_json() passes {"type": "json_object"}.
    # - Ollama supports `format: "json"` for JSON-only output.
    if response_format:
        if response_format.get("type") == "json_object":
            payload["format"] = "json"
        elif response_format.get("type") == "json":
            payload["format"] = "json"

    last_exc: Exception | None = None
    for attempt in range(1, cfg["max_retries"] + 1):
        try:
            async with httpx.AsyncClient(timeout=cfg["timeout"]) as client:
                await _wait_llm_slot()
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()

                # Map usage stats when present (best-effort).
                _usage_log.append(
                    {
                        "model": payload["model"],
                        "prompt_tokens": int(data.get("prompt_eval_count", 0) or 0),
                        "completion_tokens": int(data.get("eval_count", 0) or 0),
                        "timestamp": time.time(),
                    }
                )

                content = data.get("message", {}).get("content", "")
                return {
                    "choices": [{"message": {"content": content}}],
                    "usage": {
                        "prompt_tokens": int(data.get("prompt_eval_count", 0) or 0),
                        "completion_tokens": int(data.get("eval_count", 0) or 0),
                    },
                }

        except (httpx.HTTPStatusError, httpx.ReadTimeout, httpx.ConnectError) as exc:
            last_exc = exc
            wait = 2 ** attempt
            detail = ""
            if isinstance(exc, httpx.HTTPStatusError):
                try:
                    err_json = exc.response.json()
                    detail = err_json.get("error", {}).get("message", "") or str(err_json)
                except Exception:
                    detail = exc.response.text[:500]
            logger.warning(
                "LLM call attempt %d/%d failed (%s). %s Retrying in %ds...",
                attempt,
                cfg["max_retries"],
                exc,
                detail,
                wait,
            )
            import asyncio
            await asyncio.sleep(wait)

    message = (
        f"LLM call failed after {cfg['max_retries']} attempts for model "
        f"'{payload['model']}': {last_exc}"
    )
    if isinstance(last_exc, httpx.HTTPStatusError):
        try:
            err_json = last_exc.response.json()
            detail = err_json.get("error", {}).get("message", "") or str(err_json)
        except Exception:
            detail = last_exc.response.text[:500]
    raise RuntimeError(message) from last_exc


# ---------------------------------------------------------------------------
# Public high-level helpers
# ---------------------------------------------------------------------------

async def chat(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> str:
    """Simple chat completion — returns the assistant's text content."""

    data = await _post_chat(
        messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    message_content = data["choices"][0]["message"]["content"]
    if isinstance(message_content, str):
        return message_content
    if isinstance(message_content, list):
        parts: list[str] = []
        for item in message_content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
        return "\n".join(parts).strip()
    return str(message_content)


async def chat_json(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> dict[str, Any]:
    """Chat completion with JSON-mode — parses the response as JSON dict.

    The caller is responsible for instructing the model to output JSON in the
    system/user prompt.  This helper sets ``response_format`` and falls back
    to manual extraction if the provider ignores the flag.

    Note: Ollama Cloud uses its own `format` mechanism; we map our internal
    `response_format={"type": "json_object"}` to Ollama's `format: "json"`.
    """

    try:
        data = await _post_chat(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
    except RuntimeError as exc:
        # Some OpenRouter models (especially free/community variants) reject
        # response_format. Fallback to plain completion + robust JSON extraction.
        text = str(exc).lower()
        if "response_format" in text or "json_object" in text:
            data = await _post_chat(
                messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=None,
            )
        else:
            raise

    raw_content = data["choices"][0]["message"]["content"]
    if isinstance(raw_content, list):
        raw = "\n".join(
            str(item.get("text", ""))
            for item in raw_content
            if isinstance(item, dict)
        ).strip()
    else:
        raw = str(raw_content)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return _extract_json_from_text(raw)


async def chat_structured(
    messages: list[dict[str, str]],
    schema: dict[str, Any],
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> dict[str, Any]:
    """Chat with a JSON schema hint injected into the system prompt.

    Appends schema description so the model conforms to the expected shape
    even when the provider doesn't natively support ``json_schema``.
    """

    schema_instruction = (
        "You MUST respond with a valid JSON object that conforms to this schema:\n"
        f"```json\n{json.dumps(schema, indent=2)}\n```\n"
        "Output ONLY the JSON object, no markdown fences or explanation."
    )

    augmented = list(messages)
    if augmented and augmented[0]["role"] == "system":
        augmented[0] = {
            "role": "system",
            "content": augmented[0]["content"] + "\n\n" + schema_instruction,
        }
    else:
        augmented.insert(0, {"role": "system", "content": schema_instruction})

    return await chat_json(
        augmented,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_json_from_text(text: str) -> dict[str, Any]:
    """Best-effort JSON extraction from LLM text that may contain fences."""
    cleaned = text.strip()

    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = lines[1:]  # drop opening fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract JSON from LLM response: {text[:200]}…")
