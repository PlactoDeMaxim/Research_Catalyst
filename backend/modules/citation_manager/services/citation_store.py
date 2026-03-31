from __future__ import annotations

from datetime import datetime, timezone
import json
import uuid

from modules.core.services import postgres_store
from modules.citation_manager.models.citation_manager_models import (
    CitationProject,
    CitationRecord,
)


class _Store:
    def __init__(self) -> None:
        now = _now_iso()
        self.projects: list[CitationProject] = [
            CitationProject(
                id="citation-project-1",
                title="Local Demo Project",
                description="Fallback bibliography project for local development.",
                created_at=now,
                updated_at=now,
            )
        ]
        self.citations: list[CitationRecord] = []

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


_STORE = _Store()


def list_projects() -> list[CitationProject]:
    if postgres_store.database_enabled():
        rows = postgres_store.list_workspace_projects(kind="citation")
        return [
            CitationProject(
                id=row["id"],
                title=row["title"],
                description=row.get("description", ""),
                created_at=row.get("created_at", ""),
                updated_at=row.get("updated_at", ""),
            )
            for row in rows
        ]
    return sorted(_STORE.projects, key=lambda item: item.updated_at, reverse=True)


def create_project(title: str, description: str = "") -> CitationProject:
    if postgres_store.database_enabled():
        row = postgres_store.create_workspace_project(
            title=title,
            description=description,
            kind="citation",
        )
        return CitationProject(
            id=row["id"],
            title=row["title"],
            description=row.get("description", ""),
            created_at=row.get("created_at", ""),
            updated_at=row.get("updated_at", ""),
        )
    now = _now_iso()
    project = CitationProject(
        id=str(uuid.uuid4()),
        title=title,
        description=description,
        created_at=now,
        updated_at=now,
    )
    _STORE.projects.insert(0, project)
    return project


def list_citations(project_id: str) -> list[CitationRecord]:
    if postgres_store.database_enabled():
        rows = postgres_store.list_workspace_citations(project_id)
        return [
            CitationRecord(
                id=row["id"],
                citation_text=row["citation_text"],
                csl_json=row.get("csl_json", ""),
                project_id=row["project_id"],
                created_at=row.get("created_at", ""),
            )
            for row in rows
        ]
    return [
        citation
        for citation in sorted(_STORE.citations, key=lambda item: item.created_at, reverse=True)
        if citation.project_id == project_id
    ]


def create_citation(project_id: str, citation_text: str, csl_json: str | dict | None) -> CitationRecord:
    if postgres_store.database_enabled():
        project = postgres_store.get_workspace_project(project_id)
        if not project or project.get("kind") != "citation":
            raise ValueError("Project not found")
        row = postgres_store.create_workspace_citation(
            project_id=project_id,
            citation_text=citation_text,
            csl_json=csl_json if isinstance(csl_json, str) else json.dumps(csl_json or {}),
        )
        postgres_store.update_workspace_project(project_id, updated_at=_now_iso())
        return CitationRecord(
            id=row["id"],
            citation_text=row["citation_text"],
            csl_json=row.get("csl_json", ""),
            project_id=row["project_id"],
            created_at=row.get("created_at", ""),
        )
    project = next((item for item in _STORE.projects if item.id == project_id), None)
    if not project:
        raise ValueError("Project not found")

    citation = CitationRecord(
        id=str(uuid.uuid4()),
        citation_text=citation_text,
        csl_json=csl_json if isinstance(csl_json, str) else json.dumps(csl_json or {}),
        project_id=project_id,
        created_at=_now_iso(),
    )
    _STORE.citations.insert(0, citation)
    project.updated_at = _now_iso()
    return citation


def delete_citation(citation_id: str) -> bool:
    if postgres_store.database_enabled():
        return postgres_store.delete_workspace_citation(citation_id)
    for index, citation in enumerate(_STORE.citations):
        if citation.id != citation_id:
            continue

        del _STORE.citations[index]
        project = next((item for item in _STORE.projects if item.id == citation.project_id), None)
        if project:
            project.updated_at = _now_iso()
        return True

    return False
