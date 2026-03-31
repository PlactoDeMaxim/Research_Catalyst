"""
In-memory registry for canonical backbone entities.

This provides a migration bridge before Prisma-backed repositories are added.
"""

from __future__ import annotations

from typing import Optional

from modules.core.models.backbone_models import (
    Claim,
    Document,
    EvidenceChunk,
    ResearchProject,
)
from modules.core.services import postgres_store

_PROJECTS: dict[str, ResearchProject] = {}
_DOCUMENTS: dict[str, Document] = {}
_CHUNKS: dict[str, EvidenceChunk] = {}
_CLAIMS: dict[str, Claim] = {}


def create_project(title: str, description: str = "", owner_id: str = "local-user") -> ResearchProject:
    if postgres_store.database_enabled():
        row = postgres_store.create_workspace_project(
            title=title,
            description=description,
            owner_id=owner_id,
            kind="general",
        )
        return ResearchProject(
            id=row["id"],
            title=row["title"],
            description=row.get("description", ""),
            owner_id=row.get("owner_id", owner_id),
            created_at=row.get("created_at", ""),
            updated_at=row.get("updated_at", ""),
        )
    project = ResearchProject(title=title, description=description, owner_id=owner_id)
    _PROJECTS[project.id] = project
    return project


def list_projects() -> list[ResearchProject]:
    if postgres_store.database_enabled():
        rows = postgres_store.list_workspace_projects(kind="general")
        return [
            ResearchProject(
                id=row["id"],
                title=row["title"],
                description=row.get("description", ""),
                owner_id=row.get("owner_id", "local-user"),
                created_at=row.get("created_at", ""),
                updated_at=row.get("updated_at", ""),
            )
            for row in rows
        ]
    return sorted(_PROJECTS.values(), key=lambda p: p.created_at, reverse=True)


def get_project(project_id: str) -> Optional[ResearchProject]:
    if postgres_store.database_enabled():
        row = postgres_store.get_workspace_project(project_id)
        if not row:
            return None
        return ResearchProject(
            id=row["id"],
            title=row["title"],
            description=row.get("description", ""),
            owner_id=row.get("owner_id", "local-user"),
            created_at=row.get("created_at", ""),
            updated_at=row.get("updated_at", ""),
        )
    return _PROJECTS.get(project_id)


def add_document(project_id: str, title: str, source_type: str = "upload", mime_type: str = "text/plain") -> Document:
    if postgres_store.database_enabled():
        row = postgres_store.create_document(
            project_id=project_id,
            title=title,
            source_type=source_type,
            mime_type=mime_type,
        )
        return Document(**row)
    doc = Document(project_id=project_id, title=title, source_type=source_type, mime_type=mime_type)
    _DOCUMENTS[doc.id] = doc
    return doc


def list_documents(project_id: str) -> list[Document]:
    if postgres_store.database_enabled():
        return [Document(**row) for row in postgres_store.list_documents(project_id)]
    return [d for d in _DOCUMENTS.values() if d.project_id == project_id]


def add_evidence_chunk(project_id: str, document_id: str, content: str, chunk_index: int = 0) -> EvidenceChunk:
    if postgres_store.database_enabled():
        row = postgres_store.create_evidence_chunk(
            project_id=project_id,
            document_id=document_id,
            content=content,
            chunk_index=chunk_index,
            tokens=max(1, len(content.split())),
        )
        return EvidenceChunk(**row)
    chunk = EvidenceChunk(
        project_id=project_id,
        document_id=document_id,
        content=content,
        chunk_index=chunk_index,
        tokens=max(1, len(content.split())),
    )
    _CHUNKS[chunk.id] = chunk
    return chunk


def list_evidence(project_id: str, document_id: str | None = None) -> list[EvidenceChunk]:
    if postgres_store.database_enabled():
        return [EvidenceChunk(**row) for row in postgres_store.list_evidence_chunks(project_id, document_id)]
    data = [chunk for chunk in _CHUNKS.values() if chunk.project_id == project_id]
    if document_id:
        data = [chunk for chunk in data if chunk.document_id == document_id]
    return data


def add_claim(project_id: str, text: str, evidence_chunk_ids: list[str] | None = None) -> Claim:
    if postgres_store.database_enabled():
        row = postgres_store.create_claim(
            project_id=project_id,
            text=text,
            evidence_chunk_ids=evidence_chunk_ids or [],
        )
        return Claim(**row)
    claim = Claim(project_id=project_id, text=text, evidence_chunk_ids=evidence_chunk_ids or [])
    _CLAIMS[claim.id] = claim
    return claim


def list_claims(project_id: str) -> list[Claim]:
    if postgres_store.database_enabled():
        return [Claim(**row) for row in postgres_store.list_claims(project_id)]
    return [claim for claim in _CLAIMS.values() if claim.project_id == project_id]
