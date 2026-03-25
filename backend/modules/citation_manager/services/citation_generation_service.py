from __future__ import annotations

from datetime import datetime, timezone
import json
import re
from html import unescape
from urllib.parse import urlparse

import requests

from modules.citation_manager.models.citation_manager_models import (
    CitationGenerateResponse,
    CitationMetadata,
)


OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma3:4b"
OLLAMA_TIMEOUT = 120
REQUEST_TIMEOUT = 20
USER_AGENT = "ResearchCatalyst/0.1 CitationManager"
SUPPORTED_FORMATS = {"APA", "MLA", "IEEE", "Chicago"}


def _normalize_format(value: str) -> str:
    normalized = value.strip().lower()
    mapping = {
        "apa": "APA",
        "mla": "MLA",
        "ieee": "IEEE",
        "chicago": "Chicago",
    }
    return mapping.get(normalized, value.strip())


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def detect_doi(value: str) -> str:
    match = re.search(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", value.strip(), flags=re.IGNORECASE)
    return match.group(0) if match else ""


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _safe_url(value: str) -> str:
    cleaned = value.strip()
    if cleaned.startswith(("http://", "https://")):
        return cleaned
    doi = detect_doi(cleaned)
    if doi:
        return f"https://doi.org/{doi}"
    return f"https://{cleaned.lstrip('/')}"


def _domain_label(raw_url: str) -> str:
    try:
        hostname = urlparse(raw_url).hostname or ""
        hostname = hostname.removeprefix("www.")
        parts = hostname.split(".")
        core = " ".join(parts[:-1] or parts)
        return re.sub(r"[-_]+", " ", core).title() or "Web Source"
    except Exception:
        return "Web Source"


def _fallback_metadata(source: str) -> CitationMetadata:
    url = _safe_url(source)
    doi = detect_doi(source)
    publisher = _domain_label(url)
    year = str(datetime.now(timezone.utc).year)
    title = f"DOI Reference {doi}" if doi else publisher
    return CitationMetadata(
        title=title,
        authors=[],
        year=year,
        publisher=publisher,
        url=url,
        doi=doi or None,
        accessed_on=_today(),
    )


def _crossref_metadata(doi: str, source: str) -> CitationMetadata | None:
    response = requests.get(
        f"https://api.crossref.org/works/{requests.utils.quote(doi, safe='')}",
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT,
    )
    if response.status_code != 200:
        return None

    message = response.json().get("message", {})
    authors: list[str] = []
    for item in message.get("author", []):
        name = _normalize_whitespace(
            " ".join(part for part in [item.get("given"), item.get("family")] if part)
        )
        if not name:
            name = _normalize_whitespace(item.get("name", ""))
        if name:
            authors.append(name)

    year = str(
        message.get("issued", {})
        .get("date-parts", [[datetime.now(timezone.utc).year]])[0][0]
    )
    title = _normalize_whitespace(" ".join(message.get("title", []))) or _fallback_metadata(source).title
    return CitationMetadata(
        title=title,
        authors=authors,
        year=year,
        publisher=message.get("publisher"),
        url=message.get("URL") or _safe_url(source),
        doi=message.get("DOI") or doi,
        accessed_on=_today(),
    )


def _extract_meta(html: str, key: str, attr: str = "name") -> str:
    pattern = rf'<meta[^>]+{attr}=["\']{re.escape(key)}["\'][^>]+content=["\']([^"\']+)["\']'
    match = re.search(pattern, html, flags=re.IGNORECASE)
    if match:
        return _normalize_whitespace(unescape(match.group(1)))
    reverse_pattern = rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+{attr}=["\']{re.escape(key)}["\']'
    match = re.search(reverse_pattern, html, flags=re.IGNORECASE)
    if match:
        return _normalize_whitespace(unescape(match.group(1)))
    return ""


def _webpage_metadata(source: str) -> CitationMetadata:
    url = _safe_url(source)
    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    html = response.text

    title = (
        _extract_meta(html, "og:title", attr="property")
        or _extract_meta(html, "twitter:title", attr="name")
    )
    if not title:
        match = re.search(r"<title>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
        if match:
            title = _normalize_whitespace(unescape(match.group(1)))

    authors_raw = (
        _extract_meta(html, "author")
        or _extract_meta(html, "article:author", attr="property")
        or _extract_meta(html, "citation_author", attr="name")
    )
    publisher = (
        _extract_meta(html, "og:site_name", attr="property")
        or _extract_meta(html, "publisher")
        or _domain_label(url)
    )
    published = (
        _extract_meta(html, "article:published_time", attr="property")
        or _extract_meta(html, "citation_publication_date")
        or _extract_meta(html, "date")
    )
    year_match = re.search(r"(19|20)\d{2}", published)
    year = year_match.group(0) if year_match else str(datetime.now(timezone.utc).year)
    doi = detect_doi(source) or _extract_meta(html, "citation_doi")

    authors = [
        _normalize_whitespace(part)
        for part in re.split(r"\s*,\s*|\s+and\s+", authors_raw)
        if _normalize_whitespace(part)
    ]

    return CitationMetadata(
        title=title or _fallback_metadata(source).title,
        authors=authors,
        year=year,
        publisher=publisher,
        url=url,
        doi=doi or None,
        accessed_on=_today(),
    )


def _build_prompt(metadata: CitationMetadata, citation_format: str) -> str:
    metadata_json = json.dumps(metadata.model_dump(), ensure_ascii=True)
    return f"""You are a citation formatting assistant.

Use the metadata below to produce a citation in {citation_format} format.
Return STRICT JSON only with exactly these keys:
- citation_text: string
- in_text_citation: string

Rules:
- Do not invent metadata that is not present.
- If authors are missing, use the publisher or title as the lead element when appropriate.
- Keep the output concise and valid for academic use.
- Output valid JSON only.

Metadata:
{metadata_json}
"""


def _format_author_list(authors: list[str], citation_format: str) -> str:
    if not authors:
        return ""
    if citation_format == "IEEE":
        return ", ".join(authors[:3]) if len(authors) <= 3 else f"{authors[0]} et al."
    if len(authors) == 1:
        return authors[0]
    if len(authors) == 2:
        return f"{authors[0]} and {authors[1]}"
    return f"{authors[0]} et al."


def _fallback_citation_text(metadata: CitationMetadata, citation_format: str) -> str:
    authors = _format_author_list(metadata.authors, citation_format)
    title = metadata.title or "Untitled source"
    publisher = metadata.publisher or "Unknown publisher"
    year = metadata.year or "n.d."
    accessed = f" Accessed {metadata.accessed_on}." if metadata.accessed_on else ""
    doi_suffix = f" DOI: {metadata.doi}." if metadata.doi else ""

    if citation_format == "MLA":
        return _normalize_whitespace(
            f'{authors + ". " if authors else ""}"{title}." {publisher}, {year}, {metadata.url}.{accessed}'
        )
    if citation_format == "IEEE":
        return _normalize_whitespace(
            f'{authors + ", " if authors else ""}"{title}," {publisher}, {year}. [Online]. Available: {metadata.url}.{doi_suffix}'
        )
    if citation_format == "Chicago":
        return _normalize_whitespace(
            f'{authors + ". " if authors else ""}"{title}." {publisher}, {year}. {metadata.url}.{accessed}'
        )
    return _normalize_whitespace(
        f"{authors + '. ' if authors else ''}({year}). {title}. {publisher}. {metadata.url}.{doi_suffix}"
    )


def _fallback_in_text_citation(metadata: CitationMetadata) -> str:
    lead = (
        (metadata.authors[0].split(" ")[-1] if metadata.authors else "")
        or metadata.publisher
        or metadata.title
    )
    return _normalize_whitespace(f"({lead}, {metadata.year or 'n.d.'})")


def _extract_json_object(raw: str) -> dict:
    text = raw.strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return {}

    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _generate_with_ollama(metadata: CitationMetadata, citation_format: str) -> tuple[str, str]:
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL,
            "prompt": _build_prompt(metadata, citation_format),
            "stream": False,
            "format": "json",
        },
        timeout=OLLAMA_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    data = _extract_json_object(str(payload.get("response", "")))
    citation_text = _normalize_whitespace(
        str(
            data.get("citation_text")
            or data.get("citation")
            or data.get("citationText")
            or data.get("text")
            or ""
        )
    )
    in_text_citation = _normalize_whitespace(
        str(
            data.get("in_text_citation")
            or data.get("inTextCitation")
            or data.get("in_text")
            or ""
        )
    )
    if not citation_text:
        citation_text = _fallback_citation_text(metadata, citation_format)
    if not in_text_citation:
        in_text_citation = _fallback_in_text_citation(metadata)
    return citation_text, in_text_citation


def _to_csl_json(metadata: CitationMetadata) -> dict:
    year_value = int(metadata.year) if metadata.year.isdigit() else None
    return {
        "title": metadata.title,
        "author": [{"literal": author} for author in metadata.authors],
        "issued": {"date-parts": [[year_value]]},
        "publisher": metadata.publisher or "",
        "URL": metadata.url,
        "DOI": metadata.doi or "",
        "type": "webpage" if metadata.doi is None else "article-journal",
    }


def generate_citation(source: str, citation_format: str) -> CitationGenerateResponse:
    normalized_format = _normalize_format(citation_format)
    if normalized_format not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported citation format: {citation_format}")

    metadata = _fallback_metadata(source)
    doi = detect_doi(source)

    try:
        if doi:
            metadata = _crossref_metadata(doi, source) or metadata
        else:
            metadata = _webpage_metadata(source)
            if metadata.doi:
                metadata = _crossref_metadata(metadata.doi, source) or metadata
    except requests.RequestException:
        pass

    citation_text, in_text_citation = _generate_with_ollama(metadata, normalized_format)
    return CitationGenerateResponse(
        citation_text=citation_text,
        csl_json=_to_csl_json(metadata),
        metadata=metadata,
        in_text_citation=in_text_citation,
    )
