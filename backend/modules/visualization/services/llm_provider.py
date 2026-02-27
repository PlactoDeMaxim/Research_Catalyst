"""
LLM Provider — Groq API Integration

Provides a unified interface for calling LLMs via Groq's API.
Uses httpx for async HTTP calls.
"""

import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


async def call_llm(
    prompt: str,
    system_prompt: str = "",
    temperature: float = 0.3,
    max_tokens: int = 4096,
) -> str:
    """
    Send a prompt to Groq's API and return the text response.

    Args:
        prompt: The user message / main prompt
        system_prompt: System-level instructions
        temperature: Creativity control (lower = more deterministic)
        max_tokens: Max response length

    Returns:
        Raw text response from the LLM
    """
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set in environment variables")

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(GROQ_API_URL, json=payload, headers=headers)
        response.raise_for_status()

    data = response.json()
    return data["choices"][0]["message"]["content"]


async def call_llm_structured(
    prompt: str,
    system_prompt: str = "",
    temperature: float = 0.2,
) -> dict:
    """
    Call LLM and parse the response as JSON.
    Includes fallback parsing for slightly malformed JSON.
    """
    raw = await call_llm(prompt, system_prompt, temperature)

    # Try direct JSON parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Fallback: extract JSON from markdown code blocks
    import re
    json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", raw, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Last resort: find first { ... } block
    brace_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Failed to parse LLM response as JSON: {raw[:500]}")
