"""
Citation Service — Multi-source literature search + 4-layer verification.

Reuses the existing ``paper_search`` providers (OpenAlex, arXiv, Crossref,
Semantic Scholar) for discovery.  Adds:
  - LLM-driven query expansion
  - 4-layer citation verification (arXiv ID, DOI, Semantic Scholar title, LLM relevance)
  - Multi-round injection into paper sections
  - BibTeX generation
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import httpx

from modules.code_mapper.models.code_mapper_models import (
    CitationEntry,
    PaperSectionDraft,
    RepoStructure,
)
from modules.code_mapper.services import llm_client
from modules.paper_search.services import search_service
from modules.paper_search.providers import semantic_scholar_provider

logger = logging.getLogger(__name__)

MAX_CITATION_ROUNDS = 3
MAX_CITATIONS_PER_SECTION = 8


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def discover_citations(
    repo: RepoStructure,
    sections: list[PaperSectionDraft] | None = None,
) -> list[CitationEntry]:
    """Search for relevant literature and return verified citations.

    1. Generate search queries from repo context
    2. Search via paper_search providers
    3. Verify each candidate through 4 layers
    4. Return deduplicated, scored citations
    """

    queries = await _expand_queries(repo)
    raw_papers = await _search_literature(queries)
    candidates = _to_citation_entries(raw_papers)
    verified = await _verify_all(candidates)
    verified.sort(key=lambda c: -c.relevance_score)

    return _deduplicate(verified)[:50]


async def inject_citations(
    sections: list[PaperSectionDraft],
    citations: list[CitationEntry],
) -> list[PaperSectionDraft]:
    """Multi-round citation injection into paper section drafts."""

    cite_map = {c.cite_key: c for c in citations}
    available = _build_cite_list(citations)

    for round_num in range(1, MAX_CITATION_ROUNDS + 1):
        updated = []
        for section in sections:
            if section.section_id == "abstract":
                updated.append(section)
                continue

            improved = await _inject_round(section, available, round_num)
            updated.append(improved)
        sections = updated

    return sections


def generate_bibtex(citations: list[CitationEntry]) -> str:
    """Compile all verified citations into a .bib file string."""
    entries = []
    for c in citations:
        if c.bibtex:
            entries.append(c.bibtex)
        else:
            entries.append(_synthesize_bibtex(c))
    return "\n\n".join(entries)


# ---------------------------------------------------------------------------
# Query expansion
# ---------------------------------------------------------------------------

async def _expand_queries(repo: RepoStructure) -> list[str]:
    """Use LLM to generate 5-8 diverse search queries from repo context."""

    system = (
        "You are a research librarian. Given a code repository description, "
        "generate 5-8 diverse academic search queries that would find "
        "the most relevant related work. Include:\n"
        "- Queries about the core technique/method\n"
        "- Queries about the application domain\n"
        "- Queries about specific architectures or algorithms used\n\n"
        "Return a JSON object with a 'queries' array of strings."
    )

    context = (
        f"Repository: {repo.name}\n"
        f"Description: {repo.description}\n"
        f"Languages: {', '.join(repo.languages)}\n"
        f"README (excerpt): {repo.readme_content[:2000]}\n"
    )

    if repo.classes:
        context += "Key classes: " + ", ".join(
            c["name"] for c in repo.classes[:10]
        ) + "\n"

    try:
        result = await llm_client.chat_json(
            [{"role": "system", "content": system}, {"role": "user", "content": context}],
            max_tokens=500,
            temperature=0.5,
        )
        queries = result.get("queries", [])
        if isinstance(queries, list) and queries:
            return [str(q) for q in queries[:8]]
    except Exception:
        logger.warning("Query expansion failed; using README/description keywords fallback")

    return _keyword_fallback_queries(repo)


def _keyword_fallback_queries(repo: RepoStructure) -> list[str]:
    """Deterministic fallback queries when LLM query expansion fails.

    Goal: avoid generic repo-name-only queries (e.g., "ReportAI") by
    extracting a few high-signal keywords from README/description.
    """
    # Prefer README excerpt first; it already comes from repo analyzer.
    raw = " ".join(
        [
            repo.name or "",
            repo.description or "",
            repo.readme_content[:4000] if repo.readme_content else "",
        ]
    )

    cleaned = _strip_markdown(raw)
    tokens = _tokenize_keywords(cleaned)

    if not tokens:
        # Extreme fallback.
        return [repo.name or "machine learning"]

    # Build frequency map.
    freq: dict[str, int] = {}
    for t in tokens:
        freq[t] = freq.get(t, 0) + 1
    top = sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))[:10]
    keywords = [k for k, _ in top]

    # Build a few compact queries from top keywords.
    queries: list[str] = []
    if repo.description:
        q = repo.description.strip()
        if len(q) > 120:
            q = q[:120].rsplit(" ", 1)[0].strip()
        if q:
            queries.append(q)

    # Pair/triple keyword queries tend to work better than single tokens.
    if len(keywords) >= 2:
        queries.append(f"{keywords[0]} {keywords[1]}")
    if len(keywords) >= 3:
        queries.append(f"{keywords[0]} {keywords[2]}")
        queries.append(f"{keywords[1]} {keywords[2]}")
    if len(keywords) >= 4:
        queries.append(f"{keywords[0]} {keywords[1]} {keywords[2]}")

    # Deduplicate and cap.
    dedup: list[str] = []
    seen: set[str] = set()
    for q in queries:
        q2 = " ".join(q.split()).strip()
        if not q2 or q2.lower() in seen:
            continue
        if len(q2) > 100:
            q2 = q2[:100].rsplit(" ", 1)[0].strip()
        if q2:
            seen.add(q2.lower())
            dedup.append(q2)

    # Ensure at least 2 queries.
    if len(dedup) == 1:
        dedup.append(keywords[0])

    return dedup[:8]


def _strip_markdown(text: str) -> str:
    # Remove fenced code blocks.
    import re
    t = re.sub(r"```[\s\S]*?```", " ", text)
    # Convert markdown links: [label](url) -> label
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    # Remove inline code ticks.
    t = t.replace("`", " ")
    # Remove URLs.
    t = re.sub(r"https?://\S+", " ", t)
    # Drop HTML tags.
    t = re.sub(r"<[^>]+>", " ", t)
    return t


def _tokenize_keywords(text: str) -> list[str]:
    import re
    stop = {
        "the",
        "and",
        "for",
        "with",
        "that",
        "this",
        "from",
        "into",
        "using",
        "use",
        "based",
        "model",
        "models",
        "paper",
        "papers",
        "approach",
        "framework",
        "system",
        "report",
        "reports",
        "ai",
        "our",
        "we",
        "you",
        "will",
        "can",
        "may",
        "also",
        "such",
        "where",
        "what",
        "how",
        "not",
        "but",
        "are",
        "is",
        "was",
        "were",
    }
    # Keep alphanumerics + common tech separators.
    raw_tokens = re.findall(r"[A-Za-z][A-Za-z0-9_\\-]{2,}", text)
    tokens: list[str] = []
    for tok in raw_tokens:
        t = tok.strip().lower()
        if not t or t in stop:
            continue
        # Avoid extremely short or overly generic tokens.
        if len(t) < 3:
            continue
        tokens.append(t)
    return tokens


# ---------------------------------------------------------------------------
# Literature search (reuses paper_search module)
# ---------------------------------------------------------------------------

async def _search_literature(queries: list[str]) -> list[dict[str, Any]]:
    """Search all queries through the paper_search service."""

    all_papers: list[dict[str, Any]] = []
    for query in queries:
        try:
            response = await search_service.search(
                query=query, limit=10, open_access_only=False
            )
            for p in response.papers:
                all_papers.append(p.model_dump())
        except Exception:
            logger.warning("Search failed for query: %s", query)
            continue

    return all_papers


# ---------------------------------------------------------------------------
# Citation conversion
# ---------------------------------------------------------------------------

def _to_citation_entries(papers: list[dict[str, Any]]) -> list[CitationEntry]:
    entries: list[CitationEntry] = []
    seen_titles: set[str] = set()

    for p in papers:
        title = p.get("title", "").strip()
        if not title or title.lower() in seen_titles:
            continue
        seen_titles.add(title.lower())

        authors = p.get("authors", [])
        year = p.get("year", 0)
        first_author = authors[0].split()[-1] if authors else "unknown"
        cite_key = f"{first_author.lower()}{year}"
        cite_key = re.sub(r"[^a-z0-9]", "", cite_key)

        counter = 1
        base_key = cite_key
        while any(e.cite_key == cite_key for e in entries):
            cite_key = f"{base_key}{chr(96 + counter)}"
            counter += 1

        entries.append(
            CitationEntry(
                cite_key=cite_key,
                title=title,
                authors=authors,
                year=year,
                venue=p.get("venue", ""),
                doi=p.get("doi"),
                arxiv_id=p.get("arxiv_id"),
                url=p.get("url", ""),
                bibtex="",
                verified=False,
                relevance_score=0.0,
            )
        )

    return entries


# ---------------------------------------------------------------------------
# 4-Layer verification
# ---------------------------------------------------------------------------

async def _verify_all(candidates: list[CitationEntry]) -> list[CitationEntry]:
    # Strictly sequential verification to avoid hundreds of concurrent LLM calls
    # (and to respect OpenRouter free-tier rate limits).
    verified: list[CitationEntry] = []
    for c in candidates:
        verified.append(await _verify_single(c))
    return verified


async def _verify_single(entry: CitationEntry) -> CitationEntry:
    layers: list[str] = []
    score = 0.0

    # Layer 1: arXiv ID validation
    if entry.arxiv_id:
        valid = await _check_arxiv_id(entry.arxiv_id)
        if valid:
            layers.append("arxiv_id")
            score += 0.25

    # Layer 2: DOI validation via CrossRef
    if entry.doi:
        valid = await _check_doi(entry.doi)
        if valid:
            layers.append("doi")
            score += 0.25

    # Layer 3: Semantic Scholar title match
    title_match = await _check_semantic_scholar(entry.title)
    if title_match:
        layers.append("semantic_scholar_title")
        score += 0.25
        if "bibtex" in title_match:
            entry.bibtex = title_match["bibtex"]

    # Layer 4: LLM relevance scoring
    relevance = await _llm_relevance_score(entry)
    score += relevance * 0.25

    entry.verified = len(layers) >= 1
    entry.verification_layers = layers
    entry.relevance_score = score

    if not entry.bibtex:
        entry.bibtex = _synthesize_bibtex(entry)

    return entry


async def _check_arxiv_id(arxiv_id: str) -> bool:
    clean_id = arxiv_id.strip().split("v")[0]
    url = f"https://arxiv.org/abs/{clean_id}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.head(url, follow_redirects=True)
            return resp.status_code == 200
    except Exception:
        return False


async def _check_doi(doi: str) -> bool:
    url = f"https://api.crossref.org/works/{doi}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.head(url)
            return resp.status_code == 200
    except Exception:
        return False


async def _check_semantic_scholar(title: str) -> dict[str, Any] | None:
    try:
        data = await semantic_scholar_provider.raw_search(
            title,
            limit=1,
            fields="title,externalIds",
        )
        papers = data.get("data", [])
        if papers:
            found_title = papers[0].get("title", "")
            if _fuzzy_title_match(title, found_title):
                return {"matched": True}
    except Exception:
        pass
    return None


def _fuzzy_title_match(a: str, b: str) -> bool:
    def norm(s: str) -> str:
        return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return False
    shorter = min(len(na), len(nb))
    common = sum(1 for ca, cb in zip(na, nb) if ca == cb)
    return common / shorter > 0.8


async def _llm_relevance_score(entry: CitationEntry) -> float:
    system = (
        "Rate the academic relevance of this paper on a scale of 0.0-1.0. "
        "Return ONLY a JSON object with a 'score' field (float)."
    )
    user = f"Title: {entry.title}\nAuthors: {', '.join(entry.authors[:3])}\nYear: {entry.year}"

    try:
        result = await llm_client.chat_json(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=50,
            temperature=0.1,
        )
        return float(result.get("score", 0.5))
    except Exception:
        return 0.5


# ---------------------------------------------------------------------------
# Citation injection into sections
# ---------------------------------------------------------------------------

async def _inject_round(
    section: PaperSectionDraft,
    available_citations: str,
    round_num: int,
) -> PaperSectionDraft:
    system = (
        "You are an academic editor. Review this section and add appropriate "
        "\\cite{key} references where claims need support. Use ONLY citations "
        "from the provided list. Do not fabricate citation keys.\n\n"
        "Rules:\n"
        "- Add citations naturally within sentences\n"
        "- Do not add more than 3 new citations per round\n"
        "- Do not remove existing citations\n"
        "- Output ONLY the improved section text"
    )

    user = (
        f"Section: {section.title}\n"
        f"Round: {round_num}/{MAX_CITATION_ROUNDS}\n\n"
        f"Current text:\n{section.content}\n\n"
        f"Available citations:\n{available_citations}"
    )

    try:
        improved = await llm_client.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=3000,
            temperature=0.2,
        )

        cite_keys = []
        for m in re.finditer(r"\\cite\{([^}]+)\}", improved):
            for k in m.group(1).split(","):
                k = k.strip()
                if k and k not in cite_keys:
                    cite_keys.append(k)

        return PaperSectionDraft(
            section_id=section.section_id,
            title=section.title,
            content=improved.strip(),
            citations=cite_keys,
            word_count=len(improved.split()),
        )
    except Exception:
        logger.warning("Citation injection round %d failed for %s", round_num, section.title)
        return section


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_cite_list(citations: list[CitationEntry]) -> str:
    lines = []
    for c in citations:
        if c.verified:
            authors = ", ".join(c.authors[:3])
            lines.append(f"  {c.cite_key}: {c.title} ({authors}, {c.year})")
    return "\n".join(lines) or "No verified citations available."


def _deduplicate(entries: list[CitationEntry]) -> list[CitationEntry]:
    seen: set[str] = set()
    result: list[CitationEntry] = []
    for e in entries:
        key = e.title.lower().strip()
        if key not in seen:
            seen.add(key)
            result.append(e)
    return result


def _synthesize_bibtex(c: CitationEntry) -> str:
    authors_str = " and ".join(c.authors[:5]) if c.authors else "Unknown"
    entry_type = "article"
    fields = [
        f"  author = {{{authors_str}}}",
        f"  title = {{{c.title}}}",
        f"  year = {{{c.year}}}",
    ]
    if c.venue:
        fields.append(f"  journal = {{{c.venue}}}")
    if c.doi:
        fields.append(f"  doi = {{{c.doi}}}")
    if c.url:
        fields.append(f"  url = {{{c.url}}}")

    body = ",\n".join(fields)
    return f"@{entry_type}{{{c.cite_key},\n{body}\n}}"
