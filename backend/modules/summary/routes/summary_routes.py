"""
Summary Discovery Routes

Mounted at:
  /api/summary
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from modules.summary.models.summary_models import (
    CategoriesResponse,
    PapersListResponse,
    PaperDetail,
)
from modules.summary.services import paper_service


router = APIRouter()


@router.get("/categories", response_model=CategoriesResponse)
def categories() -> CategoriesResponse:
    try:
        return paper_service.get_categories()  # type: ignore[return-value]
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load categories: {str(exc)}")


@router.get("/papers", response_model=PapersListResponse)
def papers(
    mode: str = Query("latest", description="Sorting mode: latest|popular"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    category: str | None = Query(None, description="Optional category filter"),
) -> PapersListResponse:
    try:
        if mode not in {"latest", "popular"}:
            mode = "latest"

        return paper_service.list_papers(
            mode=mode,
            limit=limit,
            offset=offset,
            category=category,
        )  # type: ignore[return-value]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch papers: {str(exc)}")


@router.get("/papers/search", response_model=PapersListResponse)
def paper_search(
    q: str = Query(..., min_length=1, description="Search query"),
    mode: str = Query("latest", description="Sorting mode: latest|popular"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    category: str | None = Query(None, description="Optional category filter"),
) -> PapersListResponse:
    try:
        if mode not in {"latest", "popular"}:
            mode = "latest"

        return paper_service.search_papers(
            query=q,
            mode=mode,
            limit=limit,
            offset=offset,
            category=category,
        )  # type: ignore[return-value]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(exc)}")


@router.get("/papers/{slug}", response_model=PaperDetail)
def paper_by_slug(slug: str) -> PaperDetail:
    try:
        rec = paper_service.get_paper_detail(slug)
        if rec is None:
            raise HTTPException(status_code=404, detail="Paper not found")
        return rec  # type: ignore[return-value]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch paper: {str(exc)}")

