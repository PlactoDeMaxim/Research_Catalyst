"""
Citation manager routes.

Mounted at:
  /api/citation-manager
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from modules.citation_manager.models.citation_manager_models import (
    CitationCreateRequest,
    CitationGenerateRequest,
    CitationGenerateResponse,
    CitationListResponse,
    CitationProjectCreateRequest,
    CitationProjectsResponse,
)
from modules.citation_manager.services import citation_generation_service, citation_store


router = APIRouter()


@router.get("/projects", response_model=CitationProjectsResponse)
async def list_projects() -> CitationProjectsResponse:
    return CitationProjectsResponse(projects=citation_store.list_projects())


@router.post("/projects")
async def create_project(req: CitationProjectCreateRequest):
    if not req.title.strip():
        raise HTTPException(status_code=400, detail="Title is required")
    return citation_store.create_project(req.title.strip(), req.description.strip())


@router.get("/citations", response_model=CitationListResponse)
async def list_citations(project_id: str = Query(..., min_length=1)) -> CitationListResponse:
    return CitationListResponse(citations=citation_store.list_citations(project_id))


@router.post("/citations")
async def create_citation(req: CitationCreateRequest):
    if not req.project_id.strip():
        raise HTTPException(status_code=400, detail="project_id is required")
    if not req.citation_text.strip():
        raise HTTPException(status_code=400, detail="citation_text is required")

    try:
        return citation_store.create_citation(
            req.project_id.strip(),
            req.citation_text.strip(),
            req.csl_json,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/citations/{citation_id}")
async def delete_citation(citation_id: str):
    if not citation_store.delete_citation(citation_id):
        raise HTTPException(status_code=404, detail="Citation not found")
    return {"deleted": True}


@router.post("/generate", response_model=CitationGenerateResponse)
async def generate(req: CitationGenerateRequest) -> CitationGenerateResponse:
    if not req.source.strip():
        raise HTTPException(status_code=400, detail="source is required")

    try:
        return citation_generation_service.generate_citation(
            req.source.strip(),
            req.format,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Citation generation failed: {str(exc)}")
