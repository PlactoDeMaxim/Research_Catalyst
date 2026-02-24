"""
Ranking Service

Ranks papers using a weighted score combining:
  - Citation count (normalized)
  - Recency (newer papers score higher)
  - Open access bonus
"""

from datetime import datetime
from modules.paper_search.models.paper_model import Paper

# Weight configuration
WEIGHT_CITATIONS = 0.4
WEIGHT_RECENCY = 0.4
WEIGHT_OPEN_ACCESS = 0.2

CURRENT_YEAR = datetime.now().year


def _normalize_citations(count: int | None, max_count: int) -> float:
    """Normalize citation count to 0–1 using log-ish scale."""
    if count is None or count <= 0 or max_count <= 0:
        return 0.0
    return min(count / max_count, 1.0)


def _recency_score(year: int) -> float:
    """Score from 0–1: papers published recently get higher scores."""
    if year <= 0:
        return 0.0
    age = CURRENT_YEAR - year
    if age <= 0:
        return 1.0
    if age >= 30:
        return 0.0
    # Linear decay over 30 years
    return max(0.0, 1.0 - (age / 30.0))


def rank(papers: list[Paper], limit: int = 20) -> list[Paper]:
    """Rank papers by weighted score and return top `limit` results."""
    if not papers:
        return []

    # Find max citation count for normalization
    max_citations = max(
        (p.citation_count for p in papers if p.citation_count is not None),
        default=1,
    )
    max_citations = max(max_citations, 1)

    scored: list[tuple[float, Paper]] = []
    for paper in papers:
        c_score = _normalize_citations(paper.citation_count, max_citations)
        r_score = _recency_score(paper.year)
        oa_score = 1.0 if paper.open_access else 0.0

        total = (
            WEIGHT_CITATIONS * c_score
            + WEIGHT_RECENCY * r_score
            + WEIGHT_OPEN_ACCESS * oa_score
        )
        scored.append((total, paper))

    # Sort descending by score
    scored.sort(key=lambda x: x[0], reverse=True)

    return [paper for _, paper in scored[:limit]]
