from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

from modules.core.services import postgres_store, prompt_registry, retrieval_service
from modules.core.services import evidence_registry, job_bus
from modules.core.services.model_gateway import GatewayRequest, generate

router = APIRouter()


class CreateProjectRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    owner_id: str = "local-user"


class AddDocumentRequest(BaseModel):
    title: str
    source_type: str = "upload"
    mime_type: str = "text/plain"


class AddChunkRequest(BaseModel):
    content: str
    chunk_index: int = 0


class AddClaimRequest(BaseModel):
    text: str
    evidence_chunk_ids: list[str] = Field(default_factory=list)


class EditorProjectCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    storage_key: str = ""
    state: dict = Field(default_factory=dict)


class EditorProjectUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    storage_key: str | None = None
    state: dict | None = None


class IngestDocumentRequest(BaseModel):
    project_id: str
    title: str
    text: str = Field(min_length=1)
    source_type: str = "external"
    mime_type: str = "text/plain"
    metadata: dict = Field(default_factory=dict)


@router.get("/capabilities")
async def capabilities():
    return {
        "module": "core",
        "features": [
            "canonical-project-model",
            "document-evidence-registry",
            "claim-registry",
            "workspace-task-lifecycle",
            "model-gateway",
            "editor-project-persistence",
            "retrieval-foundation",
            "prompt-registry",
        ],
    }


@router.post("/projects")
async def create_project(req: CreateProjectRequest):
    return evidence_registry.create_project(req.title, req.description, req.owner_id)


@router.get("/projects")
async def list_projects():
    return {"items": evidence_registry.list_projects()}


@router.post("/projects/{project_id}/documents")
async def create_document(project_id: str, req: AddDocumentRequest):
    return evidence_registry.add_document(project_id, req.title, req.source_type, req.mime_type)


@router.get("/projects/{project_id}/documents")
async def list_documents(project_id: str):
    return {"items": evidence_registry.list_documents(project_id)}


@router.post("/projects/{project_id}/documents/{document_id}/evidence")
async def create_evidence_chunk(project_id: str, document_id: str, req: AddChunkRequest):
    return evidence_registry.add_evidence_chunk(project_id, document_id, req.content, req.chunk_index)


@router.get("/projects/{project_id}/evidence")
async def list_evidence(project_id: str, document_id: str | None = None):
    return {"items": evidence_registry.list_evidence(project_id, document_id)}


@router.post("/projects/{project_id}/claims")
async def create_claim(project_id: str, req: AddClaimRequest):
    return evidence_registry.add_claim(project_id, req.text, req.evidence_chunk_ids)


@router.get("/projects/{project_id}/claims")
async def list_claims(project_id: str):
    return {"items": evidence_registry.list_claims(project_id)}


@router.post("/tasks")
async def create_task(project_id: str, task_type: str):
    return await job_bus.create_task(project_id, task_type)


@router.get("/tasks")
async def list_tasks(project_id: str | None = None):
    return {"items": await job_bus.list_tasks(project_id)}


@router.post("/model-gateway/generate")
async def generate_text(req: GatewayRequest):
    return await generate(req)


@router.get("/prompts")
async def list_prompts(task_type: str | None = None):
    return {"items": prompt_registry.list_templates(task_type)}


@router.post("/retrieval/ingest")
async def ingest_document(req: IngestDocumentRequest):
    return retrieval_service.ingest_text_document(
        project_id=req.project_id,
        title=req.title,
        text=req.text,
        source_type=req.source_type,
        mime_type=req.mime_type,
        metadata=req.metadata,
    )


@router.get("/retrieval/search")
async def search_retrieval(project_id: str, query: str, limit: int = 5):
    return {"items": retrieval_service.search(project_id, query, limit)}


@router.get("/editor-projects")
async def list_editor_projects():
    if not postgres_store.database_enabled():
        return {"items": []}
    try:
        rows = postgres_store.list_workspace_projects(kind="editor")
        return {"items": rows}
    except Exception as exc:
        # DATABASE_URL set but Postgres not running / wrong host — avoid 500 on every editor load
        logger.warning("editor-projects list: database unreachable (%s)", exc)
        return {
            "items": [],
            "database_unavailable": True,
            "detail": "PostgreSQL is not reachable. Start Postgres, fix DATABASE_URL, or remove DATABASE_URL from .env for local dev without a database.",
        }


@router.post("/editor-projects")
async def create_editor_project(req: EditorProjectCreateRequest):
    if not postgres_store.database_enabled():
        raise HTTPException(
            status_code=503,
            detail="DATABASE_URL is not set; editor project persistence requires PostgreSQL.",
        )
    try:
        row = postgres_store.create_workspace_project(
            title=req.title,
            description=req.description,
            kind="editor",
            storage_key=req.storage_key,
            editor_state=req.state,
        )
        return row
    except Exception as exc:
        logger.warning("create_editor_project: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=(
                "PostgreSQL is not reachable. Start your database or remove DATABASE_URL from .env "
                "if you are not using Postgres locally."
            ),
        ) from exc


@router.get("/editor-projects/{project_id}")
async def get_editor_project(project_id: str):
    if not postgres_store.database_enabled():
        return {"item": None}
    try:
        row = postgres_store.get_workspace_project(project_id)
    except Exception as exc:
        logger.warning("get_editor_project: %s", exc)
        return {"item": None, "database_unavailable": True}
    if not row or row.get("kind") != "editor":
        return {"item": None}
    return {"item": row}


@router.put("/editor-projects/{project_id}")
async def update_editor_project(project_id: str, req: EditorProjectUpdateRequest):
    if not postgres_store.database_enabled():
        raise HTTPException(status_code=503, detail="DATABASE_URL is not set.")
    payload = req.model_dump(exclude_none=True)
    updates: dict[str, object] = {}
    if "title" in payload:
        updates["title"] = payload["title"]
    if "description" in payload:
        updates["description"] = payload["description"]
    if "storage_key" in payload:
        updates["storage_key"] = payload["storage_key"]
    if "state" in payload:
        updates["editor_state"] = payload["state"]

    try:
        row = postgres_store.update_workspace_project(project_id, **updates)
        return {"item": row}
    except Exception as exc:
        logger.warning("update_editor_project: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="PostgreSQL is not reachable. Start your database or fix DATABASE_URL.",
        ) from exc


@router.delete("/editor-projects/{project_id}")
async def delete_editor_project(project_id: str):
    if not postgres_store.database_enabled():
        raise HTTPException(status_code=503, detail="DATABASE_URL is not set.")
    try:
        return {"deleted": postgres_store.delete_workspace_project(project_id)}
    except Exception as exc:
        logger.warning("delete_editor_project: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="PostgreSQL is not reachable. Start your database or fix DATABASE_URL.",
        ) from exc
