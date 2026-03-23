from __future__ import annotations

from pydantic import BaseModel, Field


class CitationProject(BaseModel):
    id: str
    title: str
    description: str = ""
    created_at: str
    updated_at: str


class CitationRecord(BaseModel):
    id: str
    citation_text: str
    csl_json: str = ""
    project_id: str
    created_at: str


class CitationMetadata(BaseModel):
    title: str
    authors: list[str] = Field(default_factory=list)
    year: str = ""
    publisher: str | None = None
    url: str
    doi: str | None = None
    accessed_on: str | None = None


class CitationGenerateRequest(BaseModel):
    source: str
    format: str = "APA"


class CitationGenerateResponse(BaseModel):
    citation_text: str
    csl_json: dict
    metadata: CitationMetadata
    in_text_citation: str


class CitationCreateRequest(BaseModel):
    project_id: str
    citation_text: str
    csl_json: str | dict | None = None


class CitationProjectCreateRequest(BaseModel):
    title: str
    description: str = ""


class CitationProjectsResponse(BaseModel):
    projects: list[CitationProject] = Field(default_factory=list)


class CitationListResponse(BaseModel):
    citations: list[CitationRecord] = Field(default_factory=list)
