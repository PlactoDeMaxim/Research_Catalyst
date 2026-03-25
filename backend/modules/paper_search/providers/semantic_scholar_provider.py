"""
Semantic Scholar Provider — Citation counts and relevance.

Endpoint: https://api.semanticscholar.org/graph/v1/paper/search?query={query}
"""

import asyncio
import os
import time

import httpx
from modules.paper_search.models.paper_model import Paper

S2_BASE = "https://api.semanticscholar.org/graph/v1/paper/search"
# Strict public API pacing requested by user: 1 request / second.
_S2_MIN_INTERVAL_SECONDS = 1.0
_S2_LOCK = asyncio.Lock()
_S2_LAST_REQUEST_AT = 0.0

FIELDS = ",".join(
    [
        "paperId",
        "title",
        "abstract",
        "authors",
        "year",
        "venue",
        "externalIds",
        "url",
        "citationCount",
        "referenceCount",
        "isOpenAccess",
        "openAccessPdf",
    ]
)


async def _respect_s2_rate_limit() -> None:
    """Global process-local rate limit for Semantic Scholar requests."""
    global _S2_LAST_REQUEST_AT
    async with _S2_LOCK:
        now = time.monotonic()
        elapsed = now - _S2_LAST_REQUEST_AT
        if elapsed < _S2_MIN_INTERVAL_SECONDS:
            await asyncio.sleep(_S2_MIN_INTERVAL_SECONDS - elapsed)
        _S2_LAST_REQUEST_AT = time.monotonic()


def _s2_headers() -> dict[str, str]:
    # Lazy read so key changes in env are picked up without module re-import.
    api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "").strip()
    headers = {"Accept": "application/json"}
    if api_key:
        headers["x-api-key"] = api_key
    return headers


async def raw_search(
    query: str,
    *,
    limit: int = 25,
    fields: str = FIELDS,
    year_from: int | None = None,
    year_to: int | None = None,
    open_access_only: bool = False,
) -> dict:
    """Low-level Semantic Scholar search with auth + strict throttling."""
    params: dict = {
        "query": query,
        "limit": min(limit, 100),
        "fields": fields,
    }

    if year_from and year_to:
        params["year"] = f"{year_from}-{year_to}"
    elif year_from:
        params["year"] = f"{year_from}-"
    elif year_to:
        params["year"] = f"-{year_to}"

    if open_access_only:
        params["openAccessPdf"] = ""

    await _respect_s2_rate_limit()
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(S2_BASE, params=params, headers=_s2_headers())
        resp.raise_for_status()
        return resp.json()


async def search(
    query: str,
    *,
    year_from: int | None = None,
    year_to: int | None = None,
    open_access_only: bool = False,
    limit: int = 25,
) -> list[Paper]:
    """Search Semantic Scholar for papers matching `query`."""
    papers: list[Paper] = []
    try:
        data = await raw_search(
            query,
            limit=limit,
            fields=FIELDS,
            year_from=year_from,
            year_to=year_to,
            open_access_only=open_access_only,
        )

        for item in data.get("data", []):
            ext_ids = item.get("externalIds", {}) or {}
            doi = ext_ids.get("DOI")
            arxiv_id = ext_ids.get("ArXiv")

            year = item.get("year") or 0

            # Authors
            authors = [
                a.get("name", "")
                for a in (item.get("authors") or [])
                if a.get("name")
            ]

            # Open access PDF
            oa_pdf = item.get("openAccessPdf") or {}
            pdf_url = oa_pdf.get("url") if isinstance(oa_pdf, dict) else None

            papers.append(
                Paper(
                    id=f"s2:{item.get('paperId', '')}",
                    title=item.get("title", "") or "",
                    abstract=item.get("abstract", "") or "",
                    authors=authors,
                    year=year,
                    venue=item.get("venue", "") or "",
                    doi=doi,
                    arxiv_id=arxiv_id,
                    source="semantic_scholar",
                    url=item.get("url", ""),
                    pdf_url=pdf_url,
                    citation_count=item.get("citationCount"),
                    open_access=item.get("isOpenAccess", False) or False,
                )
            )
    except Exception as exc:
        print(f"[Semantic Scholar] Error: {exc}")

    return papers
