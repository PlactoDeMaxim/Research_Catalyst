"""
Canonical backbone models shared across modules.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class ResearchProject(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("proj"))
    title: str
    description: str = ""
    owner_id: str = "local-user"
    created_at: str = Field(default_factory=_utc_now)
    updated_at: str = Field(default_factory=_utc_now)


class Document(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("doc"))
    project_id: str
    title: str
    source_type: Literal["upload", "discovery", "generated", "external"] = "upload"
    mime_type: str = "text/plain"
    location: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=_utc_now)


class EvidenceChunk(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("ev"))
    project_id: str
    document_id: str
    content: str
    tokens: int = 0
    chunk_index: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
    embedding: Optional[list[float]] = None
    created_at: str = Field(default_factory=_utc_now)


class CitationRecord(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("cite"))
    project_id: str
    citation_text: str
    doi: Optional[str] = None
    source_url: Optional[str] = None
    metadata_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=_utc_now)


class Claim(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("claim"))
    project_id: str
    text: str
    source_document_id: Optional[str] = None
    evidence_chunk_ids: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    created_at: str = Field(default_factory=_utc_now)


class VerificationTask(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("verify"))
    project_id: str
    target_type: Literal["claim", "citation"] = "claim"
    target_id: str
    status: Literal["queued", "running", "succeeded", "failed"] = "queued"
    result: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=_utc_now)
    updated_at: str = Field(default_factory=_utc_now)


class WorkspaceTask(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("task"))
    project_id: str
    task_type: str
    status: Literal["queued", "running", "succeeded", "failed"] = "queued"
    attempt: int = 0
    duration_ms: int = 0
    payload: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)
    error_code: Optional[str] = None
    created_at: str = Field(default_factory=_utc_now)
    updated_at: str = Field(default_factory=_utc_now)
