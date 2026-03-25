"""
arXiv Provider — Open-access technical papers.

Endpoint: http://export.arxiv.org/api/query?search_query=all:{query}
Returns Atom XML which we parse with xml.etree.
"""

import xml.etree.ElementTree as ET
import re
import httpx
from modules.paper_search.models.paper_model import Paper

ARXIV_BASE = "https://export.arxiv.org/api/query"

# Atom / OpenSearch namespaces
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


def _extract_arxiv_id(entry_id: str) -> str:
    """Extract bare arXiv ID from the full URL.
    e.g. 'http://arxiv.org/abs/2301.12345v1' → '2301.12345'
    """
    parts = entry_id.rstrip("/").split("/")
    raw = parts[-1] if parts else entry_id
    # strip version suffix
    if "v" in raw:
        raw = raw[: raw.rfind("v")]
    return raw


async def search(
    query: str,
    *,
    year_from: int | None = None,
    year_to: int | None = None,
    open_access_only: bool = False,
    max_results: int = 25,
) -> list[Paper]:
    """Search the arXiv API for papers matching `query`."""
    safe_query = _sanitize_arxiv_query(query)
    params = {
        "search_query": f'all:"{safe_query}"',
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }

    papers: list[Paper] = []
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(ARXIV_BASE, params=params)
            resp.raise_for_status()

        root = ET.fromstring(resp.text)

        for entry in root.findall("atom:entry", NS):
            title = (entry.findtext("atom:title", "", NS) or "").strip().replace("\n", " ")
            summary = (entry.findtext("atom:summary", "", NS) or "").strip().replace("\n", " ")
            entry_id = entry.findtext("atom:id", "", NS) or ""
            published = entry.findtext("atom:published", "", NS) or ""
            year = int(published[:4]) if len(published) >= 4 else 0

            # Year filters (arXiv API doesn't support year filtering natively)
            if year_from and year < year_from:
                continue
            if year_to and year > year_to:
                continue

            # Authors
            authors: list[str] = []
            for author_el in entry.findall("atom:author", NS):
                name = author_el.findtext("atom:name", "", NS)
                if name:
                    authors.append(name.strip())

            # PDF link
            pdf_url: str | None = None
            for link in entry.findall("atom:link", NS):
                if link.get("title") == "pdf":
                    pdf_url = link.get("href")
                    break

            # Categories
            categories = [
                cat.get("term", "")
                for cat in entry.findall("atom:category", NS)
            ]

            arxiv_id = _extract_arxiv_id(entry_id)

            # DOI (some arXiv entries have a DOI)
            doi_el = entry.find("arxiv:doi", NS)
            doi = doi_el.text.strip() if doi_el is not None and doi_el.text else None

            papers.append(
                Paper(
                    id=f"arxiv:{arxiv_id}",
                    title=title,
                    abstract=summary,
                    authors=authors,
                    year=year,
                    venue=", ".join(categories[:3]),
                    doi=doi,
                    arxiv_id=arxiv_id,
                    source="arxiv",
                    url=entry_id,
                    pdf_url=pdf_url,
                    citation_count=None,
                    open_access=True,  # arXiv is always open access
                )
            )
    except Exception as exc:
        print(f"[arXiv] Error: {exc}")

    return papers


def _sanitize_arxiv_query(query: str) -> str:
    """Sanitize free-form/markdown-heavy text into arXiv-safe query terms."""
    q = (query or "").strip()
    if not q:
        return "machine learning"

    # Convert markdown links [text](url) -> text.
    q = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", q)
    # Remove URLs.
    q = re.sub(r"https?://\S+", " ", q)
    # Remove markdown code ticks and common punctuation noise.
    q = q.replace("`", " ")
    q = re.sub(r"[{}\[\]<>|^~]", " ", q)
    # Keep only word-ish chars and separators.
    q = re.sub(r"[^a-zA-Z0-9_\-\s]", " ", q)
    # Collapse repeated whitespace.
    q = re.sub(r"\s+", " ", q).strip()

    if not q:
        return "machine learning"
    # Keep query compact to avoid 400s on very long README content.
    return q[:180]
