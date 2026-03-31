from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from modules.citation_manager.services.citation_generation_service import detect_doi
from modules.paper_editor.models.writing_assistant_models import (
    CitationRecommendation,
    ComplianceIssue,
    ReviewerResponseItem,
)


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [part.strip() for part in parts if part.strip()]


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9]+", (text or "").lower())


_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "into",
    "were",
    "was",
    "are",
    "have",
    "has",
    "had",
    "their",
    "there",
    "which",
    "while",
    "using",
    "used",
    "our",
    "your",
    "about",
    "than",
}


def _keywords(text: str) -> set[str]:
    return {tok for tok in _tokenize(text) if len(tok) > 2 and tok not in _STOPWORDS}


def _overlap_score(a: str, b: str) -> float:
    aa = _keywords(a)
    bb = _keywords(b)
    if not aa or not bb:
        return 0.0
    return len(aa & bb) / max(len(aa), 1)


def _best_evidence_excerpt(claim: str, evidence: list[dict]) -> tuple[str, float]:
    best_excerpt = ""
    best_score = 0.0
    for item in evidence:
        excerpt = str(item.get("excerpt") or item.get("content") or "").strip()
        if not excerpt:
            continue
        score = _overlap_score(claim, excerpt)
        if score > best_score:
            best_score = score
            best_excerpt = excerpt[:280]
    return best_excerpt, round(min(best_score, 1.0), 2)


@dataclass
class _BibEntry:
    key: str
    title: str
    raw: str


def _parse_bib_entry(entry: str, idx: int) -> _BibEntry:
    key_match = re.search(r"@\w+\s*\{\s*([^,\s]+)\s*,", entry)
    title_match = re.search(r"title\s*=\s*\{([^}]+)\}", entry, flags=re.IGNORECASE)
    return _BibEntry(
        key=(key_match.group(1) if key_match else f"ref{idx + 1}"),
        title=(title_match.group(1).strip() if title_match else ""),
        raw=entry,
    )


def generate_grounded_draft(
    section_title: str,
    prompt: str,
    current_text: str,
    evidence: list[dict],
    citations: list[dict],
) -> dict:
    evidence_lines = []
    for item in evidence[:4]:
        label = str(item.get("title") or item.get("paper_id") or item.get("source") or "evidence")
        excerpt = str(item.get("excerpt") or item.get("content") or "").strip()
        if excerpt:
            evidence_lines.append(f"- {label}: {excerpt[:220]}")
    seed = prompt.strip() or f"Improve the {section_title} section."
    context_tail = current_text.strip()[-320:]
    draft = (
        f"{seed}\n\n"
        f"{context_tail if context_tail else 'This section introduces the core argument.'} "
        f"We ground the narrative in available evidence, highlight measurable outcomes, and avoid unsupported assertions. "
        f"Compared with prior work, the method demonstrates practical relevance and clear limitations that should be acknowledged.\n\n"
        f"Evidence anchors:\n"
        + ("\n".join(evidence_lines) if evidence_lines else "- No explicit evidence was supplied.")
    )
    citation_suggestions = []
    for cite in citations[:5]:
        key = str(cite.get("cite_key") or cite.get("id") or "").strip()
        if key:
            citation_suggestions.append(key)
    claim_snippets = _sentences(draft)[:3]
    notes = [
        "Draft is evidence-grounded and should be edited for final tone.",
        "Insert citations nearest to the strongest quantitative or comparative claims.",
    ]
    return {
        "drafted_text": draft,
        "citation_suggestions": citation_suggestions,
        "claim_snippets": claim_snippets,
        "notes": notes,
    }


def generate_autocomplete(prefix_text: str, section_title: str, evidence: list[dict]) -> list[str]:
    tail = prefix_text.strip()[-260:]
    tail_sentence = _sentences(tail)[-1] if _sentences(tail) else tail
    evidence_titles = [str(item.get("title") or "").strip() for item in evidence if str(item.get("title") or "").strip()]
    lead_title = evidence_titles[0] if evidence_titles else "recent evidence"
    suffixes = [
        f"Building on this point, we show how the result improves reproducibility in {section_title or 'the manuscript context'}.",
        f"This trend is consistent with {lead_title}, strengthening the empirical basis for this claim.",
        "A practical implication is that performance gains come with trade-offs in cost, generalization, and deployment complexity.",
    ]
    suggestions = [f"{tail_sentence} {suffix}".strip() for suffix in suffixes]
    return [item for item in suggestions if len(item.split()) >= 8]


def recommend_citations(text: str, bibliography_entries: list[str], evidence: list[dict]) -> list[CitationRecommendation]:
    recommendations: list[CitationRecommendation] = []
    combined_text = text + "\n" + "\n".join(str(item.get("title") or "") for item in evidence)
    for idx, raw_entry in enumerate(bibliography_entries[:20]):
        entry = _parse_bib_entry(raw_entry, idx)
        title_overlap = _overlap_score(entry.title, combined_text)
        text_overlap = _overlap_score(entry.raw, text)
        score = 0.25 + (0.55 * title_overlap) + (0.2 * text_overlap)
        reason = "Partial topical overlap with current section."
        if entry.title and entry.title.lower() in text.lower():
            score = max(score, 0.92)
            reason = "Exact title phrase appears in current text."
        elif title_overlap > 0.45:
            reason = "Strong topic overlap between title and current section."
        elif title_overlap > 0.25:
            reason = "Moderate topic overlap with section content."
        elif detect_doi(entry.raw):
            score = max(score, 0.56)
            reason = "Entry includes DOI and can support factual statements."
        recommendations.append(
            CitationRecommendation(
                cite_key=entry.key,
                reason=reason,
                confidence=round(min(max(score, 0.05), 0.99), 2),
            )
        )
    recommendations.sort(key=lambda item: item.confidence, reverse=True)
    return recommendations[:6]


def trace_claims(text: str, evidence: list[dict]) -> list[dict]:
    claims = []
    for sentence in _sentences(text)[:12]:
        if len(_tokenize(sentence)) < 5:
            continue
        best_excerpt, confidence = _best_evidence_excerpt(sentence, evidence)
        claims.append(
            {
                "claim": sentence,
                "support_excerpt": best_excerpt,
                "confidence": confidence,
            }
        )
    claims.sort(key=lambda item: item["confidence"], reverse=True)
    return claims[:8]


def review_manuscript(title: str, abstract: str, sections: list[dict]) -> dict:
    section_titles = [str(item.get("title") or "").strip() for item in sections if str(item.get("title") or "").strip()]
    section_content = " ".join(str(item.get("content") or "") for item in sections)
    strengths = []
    weaknesses = []
    revision_actions = []

    if abstract and len(_tokenize(abstract)) >= 40:
        strengths.append("Abstract includes substantial context and detail.")
    else:
        weaknesses.append("Abstract is brief; clarify motivation, method, and outcome.")

    expected = {"introduction", "method", "results", "conclusion"}
    present = {title.lower() for title in section_titles}
    missing = [name for name in expected if not any(name in entry for entry in present)]
    if not missing:
        strengths.append("Core paper sections are present.")
    else:
        weaknesses.append(f"Missing or unclear sections: {', '.join(missing)}.")

    length = len(_tokenize(section_content))
    if length > 1200:
        strengths.append("Body length supports a full technical narrative.")
    else:
        weaknesses.append("Body is short; expand method details and experimental evidence.")

    revision_actions.extend(
        [
            "Strengthen transitions between sections to improve argument flow.",
            "Add explicit claims and supporting citations in each major section.",
            "Add a short limitations paragraph in results or conclusion.",
        ]
    )
    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "revision_actions": revision_actions,
    }


def build_reviewer_responses(reviewer_comments: list[str], manuscript_context: str) -> list[ReviewerResponseItem]:
    context_hint = manuscript_context[:160] if manuscript_context else "current manuscript context"
    items = []
    for comment in reviewer_comments[:20]:
        action = "Revise manuscript text and update references where needed."
        if "experiment" in comment.lower() or "evaluation" in comment.lower():
            action = "Add or expand experimental results and evaluation discussion."
        elif "citation" in comment.lower():
            action = "Add missing citations and improve attribution of prior work."
        elif "clarity" in comment.lower() or "unclear" in comment.lower():
            action = "Rewrite the affected section for clarity and stronger structure."
        items.append(
            ReviewerResponseItem(
                comment=comment,
                draft_response=(
                    "Thank you for this comment. We have updated the manuscript accordingly and "
                    f"revised the relevant section using {context_hint} as the baseline."
                ),
                action_item=action,
            )
        )
    return items


def check_compliance(venue: str, required_sections: list[str], manuscript: str) -> dict:
    text = manuscript.lower()
    found = Counter()
    for header in re.findall(r"\\section\{([^}]+)\}", manuscript):
        found[header.strip().lower()] += 1

    issues: list[ComplianceIssue] = []
    for section in required_sections:
        section_l = section.lower().strip()
        if section_l and section_l not in found and section_l not in text:
            issues.append(
                ComplianceIssue(
                    issue=f"Missing required section: {section}",
                    severity="high",
                    fix_hint=f"Add a {section} section to match {venue or 'target venue'} requirements.",
                )
            )

    if "\\begin{abstract}" not in manuscript:
        issues.append(
            ComplianceIssue(
                issue="Abstract block not found.",
                severity="medium",
                fix_hint="Insert \\begin{abstract} ... \\end{abstract}.",
            )
        )
    if "\\bibliography{" not in manuscript and "\\printbibliography" not in manuscript:
        issues.append(
            ComplianceIssue(
                issue="Bibliography command missing.",
                severity="medium",
                fix_hint="Add \\bibliography{...} or \\printbibliography.",
            )
        )

    return {"compliant": len(issues) == 0, "issues": issues}


def assist_writer(
    *,
    section_title: str,
    goal: str,
    current_text: str,
    evidence: list[dict],
    bibliography_entries: list[str],
    reviewer_comments: list[str],
    venue: str,
    required_sections: list[str],
    all_sections: list[dict],
) -> dict:
    draft = generate_grounded_draft(
        section_title=section_title,
        prompt=goal,
        current_text=current_text,
        evidence=evidence,
        citations=[{"entry": e} for e in bibliography_entries],
    )
    auto = generate_autocomplete(current_text[-360:] or goal or "Continue this section", section_title, evidence)
    cites = recommend_citations(current_text, bibliography_entries, evidence)
    traces = trace_claims(current_text, evidence)
    review = review_manuscript(
        title=str(all_sections[0].get("title") if all_sections else "Manuscript"),
        abstract="",
        sections=all_sections,
    )
    responses = build_reviewer_responses(reviewer_comments, current_text[:1200]) if reviewer_comments else []
    compliance = check_compliance(venue, required_sections, current_text)
    return {
        "drafted_text": draft["drafted_text"],
        "autocomplete_suggestions": auto,
        "citation_recommendations": cites,
        "claim_traces": traces,
        "manuscript_review": review,
        "reviewer_response_plan": {"responses": responses},
        "compliance": compliance,
    }
