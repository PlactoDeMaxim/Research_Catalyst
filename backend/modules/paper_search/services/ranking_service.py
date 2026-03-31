"""
Ranking Service

Prioritizes true query relevance first, then metadata quality.
This prevents provider ordering from dominating the result list and introduces
soft source mixing so strong matches from multiple providers surface together.
"""

from __future__ import annotations

import math
import re
from datetime import datetime
from difflib import SequenceMatcher

from modules.paper_search.models.paper_model import Paper
from modules.paper_search.services.normalization_service import normalize_title

CURRENT_YEAR = datetime.now().year
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "of",
    "on",
    "or",
    "the",
    "to",
    "using",
    "with",
}

SOURCE_TIEBREAKER = {
    "semantic_scholar": 1.0,
    "openalex": 0.95,
    "crossref": 0.9,
    "arxiv": 0.88,
}


def _tokenize(text: str) -> list[str]:
    normalized = normalize_title(text)
    return [tok for tok in re.findall(r"[a-z0-9]+", normalized) if tok and tok not in STOPWORDS]


def _normalize_citations(count: int | None, max_count: int) -> float:
    if count is None or count <= 0 or max_count <= 0:
        return 0.0
    return min(math.log1p(count) / math.log1p(max_count), 1.0)


def _recency_score(year: int) -> float:
    if year <= 0:
        return 0.0
    age = CURRENT_YEAR - year
    if age <= 0:
        return 1.0
    if age >= 25:
        return 0.0
    return max(0.0, 1.0 - (age / 25.0))


def _token_overlap(query_tokens: list[str], target_tokens: list[str]) -> float:
    if not query_tokens or not target_tokens:
        return 0.0
    target_set = set(target_tokens)
    matched = sum(1 for tok in query_tokens if tok in target_set)
    return matched / max(len(set(query_tokens)), 1)


def _sequence_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _phrase_bonus(query_norm: str, title_norm: str) -> float:
    if not query_norm or not title_norm:
        return 0.0
    if title_norm == query_norm:
        return 1.0
    if title_norm.startswith(query_norm):
        return 0.85
    if query_norm in title_norm:
        return 0.7
    return 0.0


def _paper_base_score(query: str, paper: Paper, max_citations: int) -> float:
    query_norm = normalize_title(query)
    title_norm = normalize_title(paper.title)
    abstract_norm = normalize_title(paper.abstract)
    query_tokens = _tokenize(query)
    title_tokens = _tokenize(paper.title)
    abstract_tokens = _tokenize(paper.abstract)

    title_overlap = _token_overlap(query_tokens, title_tokens)
    abstract_overlap = _token_overlap(query_tokens, abstract_tokens)
    phrase = _phrase_bonus(query_norm, title_norm)
    title_similarity = _sequence_similarity(query_norm, title_norm)
    all_query_tokens_in_title = 1.0 if query_tokens and all(tok in set(title_tokens) for tok in set(query_tokens)) else 0.0

    c_score = _normalize_citations(paper.citation_count, max_citations)
    r_score = _recency_score(paper.year)
    oa_score = 1.0 if paper.open_access else 0.0
    source_bonus = SOURCE_TIEBREAKER.get(paper.source, 0.85)

    return (
        0.42 * phrase
        + 0.26 * title_overlap
        + 0.14 * title_similarity
        + 0.08 * abstract_overlap
        + 0.04 * all_query_tokens_in_title
        + 0.03 * c_score
        + 0.02 * r_score
        + 0.005 * oa_score
        + 0.005 * source_bonus
    )


def _interleave_by_source(scored: list[tuple[float, Paper]], limit: int) -> list[Paper]:
    """
    Greedy diversity selection over the best candidates.

    We preserve relevance while discouraging long same-source runs, which helps
    avoid OpenAlex-only blocks when strong matches from other providers exist.
    """
    if not scored:
        return []

    remaining = scored[:]
    ordered: list[Paper] = []
    recent_sources: list[str] = []
    lookahead = min(max(limit * 3, 12), len(remaining))

    while remaining and len(ordered) < limit:
        candidate_slice = remaining[:lookahead]
        best_idx = 0
        best_adjusted = float("-inf")

        for idx, (base_score, paper) in enumerate(candidate_slice):
            adjusted = base_score
            if recent_sources:
                if paper.source == recent_sources[-1]:
                    adjusted -= 0.03
                if len(recent_sources) >= 2 and paper.source == recent_sources[-2]:
                    adjusted -= 0.015
                if paper.source not in recent_sources[-2:]:
                    adjusted += 0.012
            adjusted += min(idx, 8) * -0.0015
            if adjusted > best_adjusted:
                best_adjusted = adjusted
                best_idx = idx

        _, selected = remaining.pop(best_idx)
        ordered.append(selected)
        recent_sources.append(selected.source)
        if len(recent_sources) > 3:
            recent_sources.pop(0)

    return ordered


def rank(papers: list[Paper], query: str, limit: int = 20) -> list[Paper]:
    if not papers:
        return []

    max_citations = max((p.citation_count or 0 for p in papers), default=1)
    max_citations = max(max_citations, 1)

    scored: list[tuple[float, Paper]] = []
    for paper in papers:
        score = _paper_base_score(query, paper, max_citations)
        scored.append((score, paper))

    scored.sort(
        key=lambda item: (
            item[0],
            item[1].citation_count or 0,
            item[1].open_access,
            item[1].year,
        ),
        reverse=True,
    )

    return _interleave_by_source(scored, limit)
