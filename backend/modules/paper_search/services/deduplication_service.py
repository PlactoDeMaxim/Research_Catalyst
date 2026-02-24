"""
Deduplication Service

Removes duplicate papers using a three-tier strategy:
  1. Exact DOI match
  2. arXiv ID match
  3. Fuzzy title + year + first-author match

Keeps the highest-quality version (prefers OpenAlex / Semantic Scholar).
"""

from difflib import SequenceMatcher
from modules.paper_search.models.paper_model import Paper
from modules.paper_search.services.normalization_service import (
    normalize_title,
    normalize_author_name,
    normalize_doi,
)

# Source priority — higher is better
SOURCE_PRIORITY = {
    "openalex": 4,
    "semantic_scholar": 3,
    "crossref": 2,
    "arxiv": 1,
}

FUZZY_TITLE_THRESHOLD = 0.85


def _source_score(paper: Paper) -> int:
    return SOURCE_PRIORITY.get(paper.source, 0)


def _merge_papers(existing: Paper, incoming: Paper) -> Paper:
    """Merge two duplicate papers, keeping the richest metadata."""
    # Choose the better base
    if _source_score(incoming) > _source_score(existing):
        base, other = incoming, existing
    else:
        base, other = existing, incoming

    # Fill in missing fields from the other
    return Paper(
        id=base.id,
        title=base.title or other.title,
        abstract=base.abstract or other.abstract,
        authors=base.authors if base.authors else other.authors,
        year=base.year or other.year,
        venue=base.venue or other.venue,
        doi=base.doi or other.doi,
        arxiv_id=base.arxiv_id or other.arxiv_id,
        source=base.source,
        url=base.url or other.url,
        pdf_url=base.pdf_url or other.pdf_url,
        citation_count=base.citation_count if base.citation_count is not None else other.citation_count,
        open_access=base.open_access or other.open_access,
    )


def _fuzzy_match(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def deduplicate(papers: list[Paper]) -> list[Paper]:
    """
    Deduplicate a list of papers.
    Returns a deduplicated list preserving insertion order of first occurrence.
    """
    # Index structures
    doi_map: dict[str, int] = {}      # normalized DOI → index in result
    arxiv_map: dict[str, int] = {}    # arXiv ID → index in result
    result: list[Paper] = []

    for paper in papers:
        merged = False
        norm_doi = normalize_doi(paper.doi)

        # ── Tier 1: DOI match ──
        if norm_doi and norm_doi in doi_map:
            idx = doi_map[norm_doi]
            result[idx] = _merge_papers(result[idx], paper)
            merged = True

        # ── Tier 2: arXiv ID match ──
        if not merged and paper.arxiv_id and paper.arxiv_id in arxiv_map:
            idx = arxiv_map[paper.arxiv_id]
            result[idx] = _merge_papers(result[idx], paper)
            merged = True

        # ── Tier 3: Fuzzy title + year + first author ──
        if not merged:
            norm_t = normalize_title(paper.title)
            first_author = normalize_author_name(paper.authors[0]) if paper.authors else ""

            for i, existing in enumerate(result):
                if paper.year and existing.year and paper.year != existing.year:
                    continue
                existing_t = normalize_title(existing.title)
                if _fuzzy_match(norm_t, existing_t) >= FUZZY_TITLE_THRESHOLD:
                    existing_first = normalize_author_name(existing.authors[0]) if existing.authors else ""
                    if not first_author or not existing_first or _fuzzy_match(first_author, existing_first) >= 0.8:
                        result[i] = _merge_papers(existing, paper)
                        # Update index maps
                        updated_doi = normalize_doi(result[i].doi)
                        if updated_doi:
                            doi_map[updated_doi] = i
                        if result[i].arxiv_id:
                            arxiv_map[result[i].arxiv_id] = i
                        merged = True
                        break

        # No match — add as new
        if not merged:
            idx = len(result)
            result.append(paper)
            if norm_doi:
                doi_map[norm_doi] = idx
            if paper.arxiv_id:
                arxiv_map[paper.arxiv_id] = idx

    return result
