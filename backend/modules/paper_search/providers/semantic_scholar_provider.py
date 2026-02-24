"""
Semantic Scholar Provider — Citation counts and relevance.

Endpoint: https://api.semanticscholar.org/graph/v1/paper/search?query={query}
"""

import httpx
from modules.paper_search.models.paper_model import Paper

S2_BASE = "https://api.semanticscholar.org/graph/v1/paper/search"

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


async def search(
    query: str,
    *,
    year_from: int | None = None,
    year_to: int | None = None,
    open_access_only: bool = False,
    limit: int = 25,
) -> list[Paper]:
    """Search Semantic Scholar for papers matching `query`."""
    params: dict = {
        "query": query,
        "limit": min(limit, 100),
        "fields": FIELDS,
    }

    # S2 supports year filtering
    if year_from and year_to:
        params["year"] = f"{year_from}-{year_to}"
    elif year_from:
        params["year"] = f"{year_from}-"
    elif year_to:
        params["year"] = f"-{year_to}"

    if open_access_only:
        params["openAccessPdf"] = ""

    papers: list[Paper] = []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(S2_BASE, params=params)
            resp.raise_for_status()
            data = resp.json()

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
