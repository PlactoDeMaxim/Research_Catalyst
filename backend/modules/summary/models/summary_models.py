"""
Summary Discovery Models

API response shapes for:
  - Categories
  - Papers list/search (card payload)
  - Paper detail (full payload)
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class CategoriesResponse(BaseModel):
    categories: list[str] = Field(default_factory=list)


class PaperCard(BaseModel):
    slug: str
    title: str
    authors: list[str] = Field(default_factory=list)
    category: str
    date_published: str

    # Derived fields for UI
    time_ago: str
    read_time_minutes: int

    executive_summary_preview: str

    # Optional metadata
    arxiv_number: Optional[str] = None
    original_paper_link: Optional[str] = None


class PapersListResponse(BaseModel):
    data: list[PaperCard] = Field(default_factory=list)
    total: int = 0
    hasMore: bool = False

    # Echo back pagination params (helps frontend)
    limit: int = 20
    offset: int = 0
    mode: str = "latest"


class PaperDetail(BaseModel):
    slug: str
    title: str
    authors: list[str] = Field(default_factory=list)
    category: str
    date_published: str

    time_ago: str
    read_time_minutes: int

    executive_summary: str
    detailed_breakdown: str = ""
    original_abstract: str = ""

    arxiv_number: Optional[str] = None
    original_paper_link: Optional[str] = None

