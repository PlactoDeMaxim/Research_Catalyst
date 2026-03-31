"""
text_chunker.py — Overlapping token-bounded text chunking.
Exact port from multi-agent-research-system-2.
"""

import logging
import re
from typing import List

from modules.multi_research.utils.token_utils import count_tokens, truncate_text

logger = logging.getLogger(__name__)

MAX_CHUNK_TOKENS: int = 800
OVERLAP_TOKENS: int = 100
HARD_DOC_LIMIT: int = 3000


def _split_into_sentences(text: str) -> List[str]:
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s for s in sentences if s]


def chunk_text(
    text: str,
    max_tokens: int = MAX_CHUNK_TOKENS,
    overlap_tokens: int = OVERLAP_TOKENS,
    hard_limit_chars: int = HARD_DOC_LIMIT,
) -> List[str]:
    if not text:
        return []
    if len(text) > hard_limit_chars:
        text = text[:hard_limit_chars]
        logger.debug("Document truncated to %d chars before chunking.", hard_limit_chars)

    sentences = _split_into_sentences(text)
    if not sentences:
        return [truncate_text(text, max_tokens)]

    chunks: List[str] = []
    current_sentences: List[str] = []
    current_tokens: int = 0
    overlap_buffer: str = ""

    for sentence in sentences:
        sentence_tokens = count_tokens(sentence)
        if sentence_tokens > max_tokens:
            sentence = truncate_text(sentence, max_tokens - overlap_tokens)
            sentence_tokens = count_tokens(sentence)

        if current_tokens + sentence_tokens > max_tokens:
            chunk_text_value = overlap_buffer + " ".join(current_sentences)
            chunks.append(chunk_text_value.strip())

            overlap_sentences: List[str] = []
            overlap_count = 0
            for s in reversed(current_sentences):
                tok = count_tokens(s)
                if overlap_count + tok <= overlap_tokens:
                    overlap_sentences.insert(0, s)
                    overlap_count += tok
                else:
                    break
            overlap_buffer = " ".join(overlap_sentences) + " " if overlap_sentences else ""

            current_sentences = [sentence]
            current_tokens = count_tokens(overlap_buffer) + sentence_tokens
        else:
            current_sentences.append(sentence)
            current_tokens += sentence_tokens

    if current_sentences:
        chunk_text_value = overlap_buffer + " ".join(current_sentences)
        chunks.append(chunk_text_value.strip())

    logger.info("Document split into %d chunks.", len(chunks))
    return chunks
