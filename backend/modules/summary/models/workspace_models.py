from __future__ import annotations

from pydantic import BaseModel, Field


class WorkspacePaperInput(BaseModel):
    id: str
    title: str
    abstract: str = ""
    authors: list[str] = Field(default_factory=list)
    year: int = 0
    venue: str = ""
    doi: str | None = None
    arxiv_id: str | None = None
    source: str = ""
    url: str = ""
    pdf_url: str | None = None
    citation_count: int | None = None
    open_access: bool = False


class EvidenceSnippet(BaseModel):
    paper_id: str
    title: str
    source: str
    excerpt: str
    score: float


class WorkspaceChatRequest(BaseModel):
    question: str = Field(min_length=3)
    papers: list[WorkspacePaperInput] = Field(default_factory=list)
    project_id: str | None = None


class WorkspaceChatResponse(BaseModel):
    answer: str
    evidence: list[EvidenceSnippet] = Field(default_factory=list)
    project_id: str | None = None


class ThemeItem(BaseModel):
    label: str
    count: int
    supporting_papers: list[str] = Field(default_factory=list)


class LiteratureSynthesisRequest(BaseModel):
    papers: list[WorkspacePaperInput] = Field(default_factory=list)
    focus: str = ""
    project_id: str | None = None


class LiteratureSynthesisResponse(BaseModel):
    summary: str
    themes: list[ThemeItem] = Field(default_factory=list)
    notable_papers: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    project_id: str | None = None


class ExtractionTableRequest(BaseModel):
    papers: list[WorkspacePaperInput] = Field(default_factory=list)


class ExtractionTableResponse(BaseModel):
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, str]] = Field(default_factory=list)


class GapAnalysisRequest(BaseModel):
    papers: list[WorkspacePaperInput] = Field(default_factory=list)
    topic: str = ""


class GapAnalysisResponse(BaseModel):
    common_themes: list[str] = Field(default_factory=list)
    underexplored_topics: list[str] = Field(default_factory=list)
    contradiction_signals: list[str] = Field(default_factory=list)
    project_id: str | None = None


class CollectionCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    papers: list[WorkspacePaperInput] = Field(default_factory=list)
    project_id: str | None = None


class CollectionResponse(BaseModel):
    id: str
    project_id: str | None = None
    title: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    papers: list[WorkspacePaperInput] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


class CollectionsListResponse(BaseModel):
    items: list[CollectionResponse] = Field(default_factory=list)


class ScreeningSessionCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    query: str = ""
    inclusion_criteria: str = ""
    exclusion_criteria: str = ""
    project_id: str | None = None


class ScreeningSessionResponse(BaseModel):
    id: str
    project_id: str | None = None
    title: str
    query: str = ""
    inclusion_criteria: str = ""
    exclusion_criteria: str = ""
    created_at: str = ""
    updated_at: str = ""


class ScreeningEntryDecisionRequest(BaseModel):
    paper: WorkspacePaperInput
    decision: str = Field(pattern="^(include|exclude|maybe|unreviewed)$")
    reason: str = ""
    tags: list[str] = Field(default_factory=list)


class ScreeningEntryResponse(BaseModel):
    id: str
    session_id: str
    paper_id: str
    title: str
    decision: str
    reason: str = ""
    tags: list[str] = Field(default_factory=list)
    paper: WorkspacePaperInput
    created_at: str = ""
    updated_at: str = ""


class ScreeningEntriesListResponse(BaseModel):
    items: list[ScreeningEntryResponse] = Field(default_factory=list)
