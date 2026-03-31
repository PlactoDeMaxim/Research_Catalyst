"""
token_utils.py — Token counting and text truncation utilities.
Exact port from multi-agent-research-system-2.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import tiktoken
    _ENCODING = tiktoken.get_encoding("cl100k_base")
    _TIKTOKEN_AVAILABLE = True
except ImportError:
    _TIKTOKEN_AVAILABLE = False
    logger.warning("tiktoken not found – falling back to word-count token estimation.")


def count_tokens(text: str, model: str = "gpt-4o") -> int:
    if not text:
        return 0
    if _TIKTOKEN_AVAILABLE:
        try:
            enc = tiktoken.encoding_for_model(model)
        except KeyError:
            enc = _ENCODING
        return len(enc.encode(text))
    words = len(text.split())
    return int(words / 0.75)


def truncate_text(text: str, max_tokens: int = 3000, model: str = "gpt-4o") -> str:
    if not text:
        return ""
    current_tokens = count_tokens(text, model)
    if current_tokens <= max_tokens:
        return text
    ratio = max_tokens / current_tokens
    cutoff = int(len(text) * ratio * 0.95)
    text = text[:cutoff]
    while count_tokens(text, model) > max_tokens and len(text) > 0:
        text = text[: int(len(text) * 0.95)]
    logger.debug("Text truncated to ~%d tokens.", count_tokens(text, model))
    return text


def is_within_token_limit(text: str, limit: int, model: str = "gpt-4o") -> bool:
    return count_tokens(text, model) <= limit
