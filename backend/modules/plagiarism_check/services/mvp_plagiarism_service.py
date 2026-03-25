"""
Simple plagiarism MVP service.

Strategy:
- extract text from pasted text / pdf / docx / txt
- split into section-like chunks
- query free scholarly metadata providers for likely source abstracts
- score similarity locally with lexical heuristics
- return section-level findings and lightweight rewriting guidance
"""

from __future__ import annotations

import io
import re
from collections import Counter
from difflib import SequenceMatcher
from typing import Iterable

from docx import Document
from pypdf import PdfReader

from modules.paper_search.models.paper_model import Paper
from modules.paper_search.providers import openalex_provider, semantic_scholar_provider
from modules.plagiarism_check.models.plagiarism_models import MatchSource, PlagiarismSummary, SectionFinding


STOPWORDS = {
    "the", "and", "for", "that", "with", "this", "from", "have", "has", "are", "was", "were",
    "into", "their", "using", "used", "been", "our", "your", "than", "such", "these", "those",
    "also", "can", "may", "more", "most", "between", "within", "show", "shows", "paper", "section",
    "study", "method", "methods", "result", "results", "introduction", "discussion", "conclusion",
}

COMMON_HEADINGS = {
    "abstract", "introduction", "background", "related work", "methodology", "methods",
    "experiments", "results", "discussion", "limitations", "conclusion", "references",
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z][a-zA-Z0-9\-]{2,}", text.lower())


def _preview(text: str, max_chars: int = 220) -> str:
    text = _normalize(text)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "..."


def extract_text_from_file(filename: str, content: bytes) -> str:
    suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix == ".txt":
        return content.decode("utf-8", errors="ignore")
    if suffix == ".pdf":
        reader = PdfReader(io.BytesIO(content))
        return "\n\n".join((page.extract_text() or "").strip() for page in reader.pages)
    if suffix in {".docx", ".doc"}:
        document = Document(io.BytesIO(content))
        return "\n".join(p.text for p in document.paragraphs)
    raise ValueError("Unsupported file type")


def _looks_like_heading(paragraph: str) -> bool:
    clean = paragraph.strip().strip(":").lower()
    if clean in COMMON_HEADINGS:
        return True
    words = clean.split()
    if 0 < len(words) <= 8 and clean.isupper():
        return True
    return False


def split_into_sections(text: str) -> list[tuple[str, str]]:
    paragraphs = [_normalize(p) for p in re.split(r"\n\s*\n", text) if _normalize(p)]
    sections: list[tuple[str, str]] = []
    current_title = "Section 1"
    current_parts: list[str] = []
    section_number = 1

    for paragraph in paragraphs:
        if _looks_like_heading(paragraph):
            if current_parts:
                sections.append((current_title, "\n\n".join(current_parts)))
                current_parts = []
            section_number += 1
            current_title = paragraph.strip().title()
            continue
        current_parts.append(paragraph)
        if len(" ".join(current_parts)) > 1400:
            sections.append((current_title, "\n\n".join(current_parts)))
            current_parts = []
            current_title = f"Section {section_number}"
            section_number += 1

    if current_parts:
        sections.append((current_title, "\n\n".join(current_parts)))

    filtered = [(title, body) for title, body in sections if len(body) >= 120]
    return filtered[:8]


def _top_terms(text: str, limit: int = 10) -> list[str]:
    tokens = [t for t in _tokenize(text) if t not in STOPWORDS]
    counts = Counter(tokens)
    return [word for word, _ in counts.most_common(limit)]


def build_query(title: str, body: str) -> str:
    first_sentence = re.split(r"(?<=[.!?])\s+", _normalize(body))[0]
    terms = _top_terms(f"{title} {body}", limit=8)
    query = " ".join([title] + terms)
    if len(query) < 40:
        query = first_sentence
    return query[:300]


def _jaccard(words_a: Iterable[str], words_b: Iterable[str]) -> float:
    a = set(words_a)
    b = set(words_b)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _overlap_phrases(section_text: str, source_text: str) -> list[str]:
    sec_tokens = _tokenize(section_text)
    src_tokens = set(_tokenize(source_text))
    phrases: list[str] = []
    for size in (5, 4, 3):
        for idx in range(0, max(0, len(sec_tokens) - size + 1)):
            phrase_tokens = sec_tokens[idx: idx + size]
            if all(token in src_tokens for token in phrase_tokens):
                phrase = " ".join(phrase_tokens)
                if phrase not in phrases:
                    phrases.append(phrase)
            if len(phrases) >= 4:
                return phrases
    return phrases


def _score_similarity(section_text: str, paper: Paper) -> tuple[float, list[str]]:
    source_text = _normalize(f"{paper.title}. {paper.abstract}")
    seq = SequenceMatcher(None, _normalize(section_text).lower(), source_text.lower()).ratio()
    jac = _jaccard(_tokenize(section_text), _tokenize(source_text))
    score = (seq * 0.55) + (jac * 0.45)
    phrases = _overlap_phrases(section_text, source_text)
    return min(score, 1.0), phrases


def _risk_label(score: float) -> str:
    if score >= 0.62:
        return "High overlap"
    if score >= 0.44:
        return "Review carefully"
    return "Low overlap"


def _suggestions(title: str, phrases: list[str], score: float) -> list[str]:
    suggestions: list[str] = []
    if score >= 0.62:
        suggestions.append("Add an explicit citation close to the overlapping claim.")
        suggestions.append("Rewrite the sentence structure instead of swapping a few words.")
    elif score >= 0.44:
        suggestions.append("Check whether this section needs a citation or quotation.")
        suggestions.append("Condense repeated terminology and restate the claim in your own framing.")
    else:
        suggestions.append("Keep the wording concise and cite the originating paper where appropriate.")
    if phrases:
        suggestions.append(f"Avoid reusing phrases like: {', '.join(phrases[:2])}.")
    if title.lower() == "abstract":
        suggestions.append("Abstracts should summarize contribution claims in your own wording.")
    return suggestions[:3]


async def _retrieve_candidates(query: str) -> list[Paper]:
    openalex = await openalex_provider.search(query, per_page=4)
    semantic = await semantic_scholar_provider.search(query, limit=4)
    merged: list[Paper] = []
    seen: set[str] = set()
    for paper in [*openalex, *semantic]:
        key = (paper.doi or paper.url or paper.title).lower()
        if not key or key in seen:
            continue
        seen.add(key)
        if paper.abstract:
            merged.append(paper)
    return merged[:6]


async def analyze_text(text: str) -> tuple[PlagiarismSummary, list[SectionFinding]]:
    sections = split_into_sections(text)
    findings: list[SectionFinding] = []
    source_scores: dict[str, tuple[MatchSource, float]] = {}

    for title, body in sections:
        query = build_query(title, body)
        candidates = await _retrieve_candidates(query)
        best_source: MatchSource | None = None
        best_score = 0.0
        best_phrases: list[str] = []

        for paper in candidates:
            score, phrases = _score_similarity(body, paper)
            if score > best_score:
                best_score = score
                best_phrases = phrases
                best_source = MatchSource(
                    id=paper.id,
                    title=paper.title,
                    url=paper.url or paper.pdf_url,
                    matchedWords=max(0, int(len(body.split()) * score)),
                    introduction=paper.venue or ", ".join(paper.authors[:3]),
                    sourceType=paper.source,
                    similarityScore=round(score * 100, 1),
                    overlapSnippet=_preview(paper.abstract or paper.title, 180),
                )

        if best_source:
            key = best_source.url or best_source.title or str(best_source.id)
            previous = source_scores.get(key)
            if previous is None or best_score > previous[1]:
                source_scores[key] = (best_source, best_score)

        findings.append(
            SectionFinding(
                title=title,
                textPreview=_preview(body, 280),
                similarityScore=round(best_score * 100, 1),
                riskLabel=_risk_label(best_score),
                matchedSource=best_source,
                overlappingPhrases=best_phrases,
                suggestions=_suggestions(title, best_phrases, best_score),
            )
        )

    if findings:
        aggregated = round(sum(f.similarityScore for f in findings) / len(findings), 1)
    else:
        aggregated = 0.0

    top_sources = [item[0] for item in sorted(source_scores.values(), key=lambda it: it[1], reverse=True)[:8]]
    summary = PlagiarismSummary(
        aggregatedScore=aggregated,
        identicalWords=sum(source.matchedWords for source in top_sources),
        minorChangedWords=0,
        relatedMeaningWords=0,
        topSources=top_sources,
    )
    return summary, findings
