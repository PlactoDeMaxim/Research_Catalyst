from __future__ import annotations

from datetime import datetime, timezone
import json
import uuid

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
    return sorted(_STORE.projects, key=lambda item: item.updated_at, reverse=True)


def create_project(title: str, description: str = "") -> CitationProject:
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
    return [
        citation
        for citation in sorted(_STORE.citations, key=lambda item: item.created_at, reverse=True)
        if citation.project_id == project_id
    ]


def create_citation(project_id: str, citation_text: str, csl_json: str | dict | None) -> CitationRecord:
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
    for index, citation in enumerate(_STORE.citations):
        if citation.id != citation_id:
            continue

        del _STORE.citations[index]
        project = next((item for item in _STORE.projects if item.id == citation.project_id), None)
        if project:
            project.updated_at = _now_iso()
        return True

    return False
