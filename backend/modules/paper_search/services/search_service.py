"""
Search Orchestration Service

Full pipeline:
  cache check → parallel provider calls → merge → deduplicate → rank → cache → return
"""

import asyncio
from modules.paper_search.models.paper_model import Paper, SearchResponse
from modules.paper_search.providers import (
    openalex_provider,
    arxiv_provider,
    crossref_provider,
    semantic_scholar_provider,
)
from modules.paper_search.services import (
    deduplication_service,
    ranking_service,
    cache_service,
)


async def search(
    query: str,
    *,
    year_from: int | None = None,
    year_to: int | None = None,
    open_access_only: bool = False,
    limit: int = 20,
) -> SearchResponse:
    """Execute the full search pipeline."""

    # ── 1. Check cache ──
    cache_filters = {
        "year_from": year_from,
        "year_to": year_to,
        "open_access_only": open_access_only,
        "limit": limit,
    }
    cached = cache_service.get(query, **cache_filters)
    if cached is not None:
        return cached

    # ── 2. Call all providers in parallel ──
    provider_kwargs = {
        "year_from": year_from,
        "year_to": year_to,
        "open_access_only": open_access_only,
    }

    tasks = [
        asyncio.create_task(openalex_provider.search(query, **provider_kwargs)),
        asyncio.create_task(arxiv_provider.search(query, **provider_kwargs)),
        asyncio.create_task(crossref_provider.search(query, **provider_kwargs)),
        asyncio.create_task(semantic_scholar_provider.search(query, **provider_kwargs)),
    ]

    provider_names = ["openalex", "arxiv", "crossref", "semantic_scholar"]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # ── 3. Merge results ──
    all_papers: list[Paper] = []
    sources_used: list[str] = []

    for name, result in zip(provider_names, results):
        if isinstance(result, Exception):
            print(f"[SearchService] Provider '{name}' failed: {result}")
            continue
        if result:
            all_papers.extend(result)
            sources_used.append(name)

    # ── 4. Deduplicate ──
    unique_papers = deduplication_service.deduplicate(all_papers)

    # ── 5. Filter open-access only (post-merge, since some providers don't filter natively) ──
    if open_access_only:
        unique_papers = [p for p in unique_papers if p.open_access]

    # ── 6. Rank ──
    ranked_papers = ranking_service.rank(unique_papers, limit=limit)

    # ── 7. Build response ──
    response = SearchResponse(
        papers=ranked_papers,
        total_results=len(unique_papers),
        sources_used=sources_used,
    )

    # ── 8. Cache ──
    cache_service.set(query, response, **cache_filters)

    return response
