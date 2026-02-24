"""
Unified Paper model for the Paper Discovery Service.

All external API providers normalize their results into this schema.
"""

from pydantic import BaseModel, Field
from typing import Optional


class Paper(BaseModel):
    """Unified paper schema across all providers."""

    id: str
    title: str
    abstract: str = ""
    authors: list[str] = Field(default_factory=list)
    year: int = 0
    venue: str = ""
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    source: str = ""  # e.g. "openalex", "arxiv", "crossref", "semantic_scholar"
    url: str = ""
    pdf_url: Optional[str] = None
    citation_count: Optional[int] = None
    open_access: bool = False

    # Phase 2 — placeholder for vector embeddings
    embedding: Optional[list[float]] = None


class SearchResponse(BaseModel):
    """Response shape for the search endpoint."""

    papers: list[Paper]
    total_results: int
    sources_used: list[str]
