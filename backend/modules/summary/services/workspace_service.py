from __future__ import annotations

import re
from collections import Counter
from typing import Any

from modules.core.services import postgres_store, retrieval_service
from modules.summary.models.workspace_models import WorkspacePaperInput

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
    "in",
    "into",
    "is",
    "of",
    "on",
    "or",
    "our",
    "paper",
    "that",
    "the",
    "their",
    "this",
    "to",
    "using",
    "we",
    "with",
}

METHOD_KEYWORDS = [
    "transformer",
    "bert",
    "gpt",
    "llm",
    "diffusion",
    "cnn",
    "rnn",
    "graph neural network",
    "retrieval augmented generation",
    "rag",
    "reinforcement learning",
    "bayesian",
    "survey",
    "systematic review",
    "benchmark",
]

DATASET_KEYWORDS = [
    "imagenet",
    "cifar",
    "mnist",
    "mmlu",
    "squad",
    "pubmed",
    "wikitext",
    "common crawl",
    "openalex",
    "crossref",
    "semantic scholar",
    "arxiv",
]

CONTRADICTION_MARKERS = [
    ("improves", "worse"),
    ("outperforms", "underperforms"),
    ("increases", "decreases"),
    ("reduces", "increases"),
]


def _paper_text(paper: WorkspacePaperInput) -> str:
    return " ".join(
        [
            paper.title,
            paper.abstract,
            " ".join(paper.authors),
            paper.venue,
            paper.source,
        ]
    ).strip()


def _tokens(text: str) -> list[str]:
    return [tok for tok in re.findall(r"[a-z0-9]+", text.lower()) if len(tok) > 2 and tok not in STOPWORDS]


def _top_keywords(papers: list[WorkspacePaperInput], limit: int = 8) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter()
    for paper in papers:
        counter.update(set(_tokens(_paper_text(paper))))
    return counter.most_common(limit)


def _infer_methods(text: str) -> str:
    found = [kw for kw in METHOD_KEYWORDS if kw in text.lower()]
    return ", ".join(found[:3]) if found else "not explicit"


def _infer_datasets(text: str) -> str:
    found = [kw for kw in DATASET_KEYWORDS if kw in text.lower()]
    return ", ".join(found[:3]) if found else "not explicit"


def _supporting_titles(papers: list[WorkspacePaperInput], keyword: str) -> list[str]:
    supported = [paper.title for paper in papers if keyword in _paper_text(paper).lower()]
    return supported[:4]


def _heuristic_score(question: str, paper: WorkspacePaperInput) -> float:
    q_tokens = set(_tokens(question))
    if not q_tokens:
        return 0.0
    title_tokens = set(_tokens(paper.title))
    abstract_tokens = set(_tokens(paper.abstract))
    title_overlap = len(q_tokens & title_tokens) / max(len(q_tokens), 1)
    abstract_overlap = len(q_tokens & abstract_tokens) / max(len(q_tokens), 1)
    phrase = 1.0 if question.lower().strip() in paper.title.lower() else 0.0
    citation_signal = min((paper.citation_count or 0) / 1000.0, 1.0)
    return round(0.5 * title_overlap + 0.25 * abstract_overlap + 0.2 * phrase + 0.05 * citation_signal, 4)


def _ensure_project(project_id: str | None, title: str, kind: str) -> str | None:
    if project_id:
        return project_id
    if not postgres_store.database_enabled():
        return None
    row = postgres_store.create_workspace_project(title=title, kind=kind)
    return str(row["id"])


def _materialize_papers(project_id: str | None, papers: list[WorkspacePaperInput]) -> None:
    if not project_id:
        return
    existing = postgres_store.list_documents(project_id) if postgres_store.database_enabled() else []
    existing_external_ids = {
        str((row.get("metadata") or {}).get("external_paper_id"))
        for row in existing
        if (row.get("metadata") or {}).get("external_paper_id")
    }
    for paper in papers:
        if paper.id in existing_external_ids:
            continue
        retrieval_service.ingest_text_document(
            project_id=project_id,
            title=paper.title,
            text=_paper_text(paper),
            source_type="discovery",
            mime_type="text/plain",
            metadata={
                "external_paper_id": paper.id,
                "source": paper.source,
                "year": paper.year,
                "doi": paper.doi,
                "url": paper.url,
            },
        )


def run_workspace_chat(question: str, papers: list[WorkspacePaperInput], project_id: str | None = None) -> dict[str, Any]:
    project_id = _ensure_project(project_id, "Literature Chat Workspace", "literature_review")
    _materialize_papers(project_id, papers)
    ranked = sorted(
        papers,
        key=lambda paper: (_heuristic_score(question, paper), paper.citation_count or 0, paper.year),
        reverse=True,
    )
    top = ranked[:3]
    if not top:
        return {"answer": "No papers were provided for analysis.", "evidence": [], "project_id": project_id}
    evidence = [
        {
            "paper_id": paper.id,
            "title": paper.title,
            "source": paper.source,
            "excerpt": (paper.abstract or paper.title)[:280],
            "score": _heuristic_score(question, paper),
        }
        for paper in top
    ]
    answer = (
        f"Across {len(papers)} selected papers, the strongest evidence for '{question}' comes from "
        f"{'; '.join(f'{paper.title} ({paper.source})' for paper in top)}. "
        f"The common thread is that {'; '.join((paper.abstract or paper.title)[:160] for paper in top)}."
    )
    return {"answer": answer, "evidence": evidence, "project_id": project_id}


def synthesize_literature(papers: list[WorkspacePaperInput], focus: str = "", project_id: str | None = None) -> dict[str, Any]:
    project_id = _ensure_project(project_id, "Literature Synthesis Workspace", "literature_review")
    _materialize_papers(project_id, papers)
    keywords = _top_keywords(papers, limit=6)
    themes = [
        {
            "label": keyword,
            "count": count,
            "supporting_papers": _supporting_titles(papers, keyword),
        }
        for keyword, count in keywords
    ]
    notable = [paper.title for paper in sorted(papers, key=lambda p: (p.citation_count or 0, p.year), reverse=True)[:5]]
    gaps = [
        f"Limited coverage around '{keyword}' beyond {count} papers." for keyword, count in keywords[-3:] if count <= max(2, len(papers) // 3)
    ]
    if not gaps:
        gaps = ["The corpus appears concentrated; add contrarian or newer papers to expose weaker-covered subtopics."]
    focus_text = f" with focus on {focus}" if focus.strip() else ""
    summary = (
        f"This literature set{focus_text} is centered on "
        f"{', '.join(keyword for keyword, _ in keywords[:4])}. "
        f"The most visible anchor papers are {', '.join(notable[:3])}."
    )
    return {
        "summary": summary,
        "themes": themes,
        "notable_papers": notable,
        "gaps": gaps,
        "project_id": project_id,
    }


def build_extraction_table(papers: list[WorkspacePaperInput]) -> dict[str, Any]:
    rows = []
    for paper in papers:
        text = _paper_text(paper)
        rows.append(
            {
                "title": paper.title,
                "year": str(paper.year or ""),
                "source": paper.source,
                "venue": paper.venue or "",
                "citations": str(paper.citation_count or 0),
                "open_access": "yes" if paper.open_access else "no",
                "methods": _infer_methods(text),
                "datasets": _infer_datasets(text),
            }
        )
    return {
        "columns": ["title", "year", "source", "venue", "citations", "open_access", "methods", "datasets"],
        "rows": rows,
    }


def analyze_gaps(papers: list[WorkspacePaperInput], topic: str = "", project_id: str | None = None) -> dict[str, Any]:
    project_id = _ensure_project(project_id, "Gap Analysis Workspace", "literature_review")
    _materialize_papers(project_id, papers)
    keywords = _top_keywords(papers, limit=10)
    common = [keyword for keyword, _ in keywords[:5]]
    underexplored = [keyword for keyword, count in keywords if count <= max(2, len(papers) // 4)]
    contradiction_signals: list[str] = []
    corpus = " ".join(_paper_text(paper).lower() for paper in papers)
    for positive, negative in CONTRADICTION_MARKERS:
        if positive in corpus and negative in corpus:
            contradiction_signals.append(f"Mixed signals detected: some papers mention '{positive}' while others mention '{negative}'.")
    if topic and not underexplored:
        underexplored.append(f"Add more papers directly targeting '{topic}' to improve gap confidence.")
    return {
        "common_themes": common,
        "underexplored_topics": underexplored[:6],
        "contradiction_signals": contradiction_signals[:5],
        "project_id": project_id,
    }


def create_collection(
    *,
    title: str,
    description: str,
    tags: list[str],
    papers: list[WorkspacePaperInput],
    project_id: str | None = None,
) -> dict[str, Any]:
    project_id = _ensure_project(project_id, title, "literature_collection")
    _materialize_papers(project_id, papers)
    row = postgres_store.create_literature_collection(
        title=title,
        description=description,
        tags=tags,
        papers=[paper.model_dump() for paper in papers],
        project_id=project_id,
    )
    return row


def list_collections(project_id: str | None = None) -> list[dict[str, Any]]:
    return postgres_store.list_literature_collections(project_id) if postgres_store.database_enabled() else []


def create_screening_session(
    *,
    title: str,
    query: str,
    inclusion_criteria: str,
    exclusion_criteria: str,
    project_id: str | None = None,
) -> dict[str, Any]:
    project_id = _ensure_project(project_id, title, "screening")
    return postgres_store.create_screening_session(
        title=title,
        query=query,
        inclusion_criteria=inclusion_criteria,
        exclusion_criteria=exclusion_criteria,
        project_id=project_id,
    )


def list_screening_sessions(project_id: str | None = None) -> list[dict[str, Any]]:
    return postgres_store.list_screening_sessions(project_id) if postgres_store.database_enabled() else []


def decide_screening_entry(
    *,
    session_id: str,
    paper: WorkspacePaperInput,
    decision: str,
    reason: str,
    tags: list[str],
) -> dict[str, Any]:
    session = postgres_store.get_screening_session(session_id)
    if session and session.get("project_id"):
        _materialize_papers(str(session["project_id"]), [paper])
    return postgres_store.upsert_screening_entry(
        session_id=session_id,
        paper_id=paper.id,
        title=paper.title,
        decision=decision,
        reason=reason,
        tags=tags,
        paper=paper.model_dump(),
    )


def list_screening_entries(session_id: str) -> list[dict[str, Any]]:
    return postgres_store.list_screening_entries(session_id) if postgres_store.database_enabled() else []
