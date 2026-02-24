"""
Crossref Provider — DOI normalization and metadata enrichment.

Endpoint: https://api.crossref.org/works?query={query}
"""

import httpx
from modules.paper_search.models.paper_model import Paper

CROSSREF_BASE = "https://api.crossref.org/works"


def _extract_authors(author_list: list[dict]) -> list[str]:
    names: list[str] = []
    for a in author_list:
        given = a.get("given", "")
        family = a.get("family", "")
        full = f"{given} {family}".strip()
        if full:
            names.append(full)
    return names


async def search(
    query: str,
    *,
    year_from: int | None = None,
    year_to: int | None = None,
    open_access_only: bool = False,
    rows: int = 25,
) -> list[Paper]:
    """Search Crossref for papers matching `query`."""
    params: dict = {
        "query": query,
        "rows": rows,
        "sort": "relevance",
        "order": "desc",
        "mailto": "research-catalyst@example.com",
    }

    # Crossref supports filter by date
    filters: list[str] = []
    if year_from:
        filters.append(f"from-pub-date:{year_from}")
    if year_to:
        filters.append(f"until-pub-date:{year_to}")
    if filters:
        params["filter"] = ",".join(filters)

    papers: list[Paper] = []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(CROSSREF_BASE, params=params)
            resp.raise_for_status()
            data = resp.json()

        items = data.get("message", {}).get("items", [])
        for item in items:
            title_list = item.get("title", [])
            title = title_list[0] if title_list else ""

            # Year from date-parts
            year = 0
            issued = item.get("issued", {})
            date_parts = issued.get("date-parts", [[]])
            if date_parts and date_parts[0] and date_parts[0][0]:
                year = int(date_parts[0][0])

            if year_from and year < year_from:
                continue
            if year_to and year > year_to:
                continue

            doi = item.get("DOI", "")

            # Venue
            container = item.get("container-title", [])
            venue = container[0] if container else ""

            # URL
            url = item.get("URL", f"https://doi.org/{doi}" if doi else "")

            # Citation count (if available)
            citation_count = item.get("is-referenced-by-count")

            papers.append(
                Paper(
                    id=f"crossref:{doi}" if doi else f"crossref:{title[:40]}",
                    title=title,
                    abstract="",  # Crossref rarely provides abstracts
                    authors=_extract_authors(item.get("author", [])),
                    year=year,
                    venue=venue,
                    doi=doi or None,
                    arxiv_id=None,
                    source="crossref",
                    url=url,
                    pdf_url=None,
                    citation_count=citation_count,
                    open_access=False,
                )
            )
    except Exception as exc:
        print(f"[Crossref] Error: {exc}")

    return papers
