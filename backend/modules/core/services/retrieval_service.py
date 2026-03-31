"""
Retrieval foundation for Phase 1.

Uses deterministic hashed embeddings so the product can support persistent
chunking, indexing, and similarity search before a full embedding provider is
introduced.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Any

from modules.core.services import evidence_registry, postgres_store

_DIM = 64


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def _embed(text: str) -> list[float]:
    vector = [0.0] * _DIM
    for token in _tokenize(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        bucket = digest[0] % _DIM
        vector[bucket] += 1.0
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))


def _chunk_text(text: str, chunk_size: int = 700, overlap: int = 120) -> list[str]:
    words = (text or "").split()
    if not words:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(len(words), start + chunk_size)
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = max(start + 1, end - overlap)
    return chunks


def ingest_text_document(
    *,
    project_id: str,
    title: str,
    text: str,
    source_type: str = "external",
    mime_type: str = "text/plain",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    document = evidence_registry.add_document(project_id, title, source_type=source_type, mime_type=mime_type)
    chunk_ids: list[str] = []
    for index, chunk_text in enumerate(_chunk_text(text)):
        embedding = _embed(chunk_text)
        if postgres_store.database_enabled():
            row = postgres_store.create_evidence_chunk(
                project_id=project_id,
                document_id=document.id,
                content=chunk_text,
                tokens=max(1, len(chunk_text.split())),
                chunk_index=index,
                metadata=metadata or {},
                embedding=embedding,
            )
            chunk_ids.append(str(row["id"]))
        else:
            chunk = evidence_registry.add_evidence_chunk(project_id, document.id, chunk_text, chunk_index=index)
            chunk_ids.append(chunk.id)
    return {"document_id": document.id, "chunk_ids": chunk_ids}


def search(project_id: str, query: str, limit: int = 5) -> list[dict[str, Any]]:
    query_vec = _embed(query)
    chunks = evidence_registry.list_evidence(project_id)
    scored: list[dict[str, Any]] = []
    for chunk in chunks:
        embedding = chunk.embedding or _embed(chunk.content)
        score = _cosine(query_vec, embedding)
        scored.append(
            {
                "id": chunk.id,
                "document_id": chunk.document_id,
                "content": chunk.content,
                "score": round(score, 4),
                "metadata": chunk.metadata,
            }
        )
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[: max(1, limit)]
