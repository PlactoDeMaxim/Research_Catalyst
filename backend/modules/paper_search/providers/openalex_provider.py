"""
OpenAlex Provider — Primary metadata source.

Endpoint: https://api.openalex.org/works?search={query}
"""

import httpx
from modules.paper_search.models.paper_model import Paper

OPENALEX_BASE = "https://api.openalex.org/works"


def _invert_abstract(inverted_index: dict | None) -> str:
    """Convert OpenAlex inverted abstract index back to plain text."""
    if not inverted_index:
        return ""
    word_positions: list[tuple[int, str]] = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort(key=lambda x: x[0])
    return " ".join(w for _, w in word_positions)


def _extract_authors(authorships: list[dict]) -> list[str]:
    names: list[str] = []
    for a in authorships:
        author = a.get("author", {})
        name = author.get("display_name", "")
        if name:
            names.append(name)
    return names


async def search(
    query: str,
    *,
    year_from: int | None = None,
    year_to: int | None = None,
    open_access_only: bool = False,
    per_page: int = 25,
) -> list[Paper]:
    """Search OpenAlex for papers matching `query`."""
    params: dict = {
        "search": query,
        "per_page": per_page,
        "mailto": "research-catalyst@example.com",
    }

    # Build filter string
    filters: list[str] = []
    if year_from:
        filters.append(f"publication_year:>{year_from - 1}")
    if year_to:
        filters.append(f"publication_year:<{year_to + 1}")
    if open_access_only:
        filters.append("is_oa:true")
    if filters:
        params["filter"] = ",".join(filters)

    papers: list[Paper] = []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(OPENALEX_BASE, params=params)
            resp.raise_for_status()
            data = resp.json()

        for work in data.get("results", []):
            oa_info = work.get("open_access", {})
            primary_location = work.get("primary_location", {}) or {}
            source = primary_location.get("source", {}) or {}

            papers.append(
                Paper(
                    id=work.get("id", ""),
                    title=work.get("title", "") or "",
                    abstract=_invert_abstract(
                        work.get("abstract_inverted_index")
                    ),
                    authors=_extract_authors(work.get("authorships", [])),
                    year=work.get("publication_year", 0) or 0,
                    venue=source.get("display_name", "") or "",
                    doi=work.get("doi"),
                    arxiv_id=None,
                    source="openalex",
                    url=work.get("id", ""),
                    pdf_url=oa_info.get("oa_url"),
                    citation_count=work.get("cited_by_count"),
                    open_access=oa_info.get("is_oa", False),
                )
            )
    except Exception as exc:
        print(f"[OpenAlex] Error: {exc}")

    return papers
