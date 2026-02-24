"""
Search Routes

GET /api/papers/search — Unified paper search endpoint.
"""

from fastapi import APIRouter, Query, HTTPException
from modules.paper_search.models.paper_model import SearchResponse
from modules.paper_search.services import search_service

router = APIRouter()


@router.get("/search", response_model=SearchResponse)
async def search_papers(
    query: str = Query(..., min_length=1, description="Search query"),
    year_from: int | None = Query(None, description="Filter: minimum publication year"),
    year_to: int | None = Query(None, description="Filter: maximum publication year"),
    open_access_only: bool = Query(False, description="Filter: open access papers only"),
    limit: int = Query(20, ge=1, le=100, description="Max results to return"),
) -> SearchResponse:
    """
    Search for research papers across OpenAlex, arXiv, Crossref, and Semantic Scholar.

    Results are deduplicated, ranked by relevance (citations + recency + OA), and cached for 24h.
    """
    try:
        result = await search_service.search(
            query=query,
            year_from=year_from,
            year_to=year_to,
            open_access_only=open_access_only,
            limit=limit,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(exc)}")
