"""
Summary Discovery Routes

Mounted at:
  /api/summary
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, UploadFile, File

from modules.summary.models.summary_models import (
    CategoriesResponse,
    PapersListResponse,
    PaperDetail,
)
from modules.summary.models.workspace_models import (
    CollectionCreateRequest,
    CollectionResponse,
    CollectionsListResponse,
    ExtractionTableRequest,
    ExtractionTableResponse,
    GapAnalysisRequest,
    GapAnalysisResponse,
    LiteratureSynthesisRequest,
    LiteratureSynthesisResponse,
    ScreeningEntriesListResponse,
    ScreeningEntryDecisionRequest,
    ScreeningEntryResponse,
    ScreeningSessionCreateRequest,
    ScreeningSessionResponse,
    WorkspaceChatRequest,
    WorkspaceChatResponse,
)
from modules.summary.services import paper_service, workspace_service



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


@router.post("/workspace/chat", response_model=WorkspaceChatResponse)
def workspace_chat(req: WorkspaceChatRequest) -> WorkspaceChatResponse:
    try:
        return WorkspaceChatResponse(**workspace_service.run_workspace_chat(req.question, req.papers, req.project_id))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Workspace chat failed: {str(exc)}")


@router.post("/workspace/synthesize", response_model=LiteratureSynthesisResponse)
def workspace_synthesize(req: LiteratureSynthesisRequest) -> LiteratureSynthesisResponse:
    try:
        return LiteratureSynthesisResponse(**workspace_service.synthesize_literature(req.papers, req.focus, req.project_id))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {str(exc)}")


@router.post("/workspace/extract-table", response_model=ExtractionTableResponse)
def workspace_extract_table(req: ExtractionTableRequest) -> ExtractionTableResponse:
    try:
        return ExtractionTableResponse(**workspace_service.build_extraction_table(req.papers))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Table extraction failed: {str(exc)}")


@router.post("/workspace/gap-analysis", response_model=GapAnalysisResponse)
def workspace_gap_analysis(req: GapAnalysisRequest) -> GapAnalysisResponse:
    try:
        return GapAnalysisResponse(**workspace_service.analyze_gaps(req.papers, req.topic))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Gap analysis failed: {str(exc)}")


@router.get("/workspace/collections", response_model=CollectionsListResponse)
def list_collections(project_id: str | None = Query(None)) -> CollectionsListResponse:
    try:
        items = [CollectionResponse(**item) for item in workspace_service.list_collections(project_id)]
        return CollectionsListResponse(items=items)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to list collections: {str(exc)}")


@router.post("/workspace/collections", response_model=CollectionResponse)
def create_collection(req: CollectionCreateRequest) -> CollectionResponse:
    try:
        return CollectionResponse(
            **workspace_service.create_collection(
                title=req.title,
                description=req.description,
                tags=req.tags,
                papers=req.papers,
                project_id=req.project_id,
            )
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to create collection: {str(exc)}")


@router.get("/workspace/screening-sessions")
def list_screening_sessions(project_id: str | None = Query(None)) -> list[ScreeningSessionResponse]:
    try:
        return [ScreeningSessionResponse(**item) for item in workspace_service.list_screening_sessions(project_id)]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to list screening sessions: {str(exc)}")


@router.post("/workspace/screening-sessions", response_model=ScreeningSessionResponse)
def create_screening_session(req: ScreeningSessionCreateRequest) -> ScreeningSessionResponse:
    try:
        return ScreeningSessionResponse(
            **workspace_service.create_screening_session(
                title=req.title,
                query=req.query,
                inclusion_criteria=req.inclusion_criteria,
                exclusion_criteria=req.exclusion_criteria,
                project_id=req.project_id,
            )
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to create screening session: {str(exc)}")


@router.get("/workspace/screening-sessions/{session_id}/entries", response_model=ScreeningEntriesListResponse)
def list_screening_entries(session_id: str) -> ScreeningEntriesListResponse:
    try:
        items = [ScreeningEntryResponse(**item) for item in workspace_service.list_screening_entries(session_id)]
        return ScreeningEntriesListResponse(items=items)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to list screening entries: {str(exc)}")


@router.post("/workspace/screening-sessions/{session_id}/entries", response_model=ScreeningEntryResponse)
def create_screening_entry(session_id: str, req: ScreeningEntryDecisionRequest) -> ScreeningEntryResponse:
    try:
        return ScreeningEntryResponse(
            **workspace_service.decide_screening_entry(
                session_id=session_id,
                paper=req.paper,
                decision=req.decision,
                reason=req.reason,
                tags=req.tags,
            )
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save screening decision: {str(exc)}")


@router.post("/upload", response_model=PaperDetail)
async def upload_paper(file: UploadFile = File(...)) -> PaperDetail:
    """Upload a PDF paper, extract text, and generate an AI summary."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    try:
        file_bytes = await file.read()
        if len(file_bytes) < 100:
            raise HTTPException(status_code=400, detail="File is too small or empty")
        if len(file_bytes) > 50 * 1024 * 1024:  # 50MB limit
            raise HTTPException(status_code=400, detail="File is too large (max 50MB)")

        from modules.summary.services.pdf_summarizer import summarize_pdf
        paper = await summarize_pdf(file_bytes, file.filename)

        # Register in the in-memory store so it can be looked up by slug
        paper_service.register_uploaded_paper(paper)

        return PaperDetail(**{k: v for k, v in paper.items() if k in PaperDetail.model_fields})
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Summarization failed: {str(exc)}")


@router.get("/uploaded")
def uploaded_papers() -> list[dict]:
    """List all uploaded paper summaries."""
    try:
        return paper_service.list_uploaded_papers()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to list uploaded papers: {str(exc)}")
