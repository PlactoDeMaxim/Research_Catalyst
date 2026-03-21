from __future__ import annotations

from modules.paper_editor.models.paper_editor_models import StructuredPaper


def _get_section_title(paper: StructuredPaper, section_id: str) -> str:
    for sec in paper.sections:
        if sec.id == section_id:
            return sec.title or section_id
    return section_id


def _get_neighbor_text(paper: StructuredPaper, section_id: str) -> str:
    ids = [s.id for s in paper.sections]
    if section_id not in ids:
        return ""
    idx = ids.index(section_id)
    parts: list[str] = []
    if idx > 0:
        prev = paper.sections[idx - 1]
        parts.append(f"Previous section ({prev.title}): {prev.content[:350]}")
    if idx < len(paper.sections) - 1:
        nxt = paper.sections[idx + 1]
        parts.append(f"Next section ({nxt.title}): {nxt.content[:220]}")
    return "\n".join(parts)


def _compose_base_content(paper: StructuredPaper, section_id: str) -> str:
    sec_title = _get_section_title(paper, section_id)
    context = paper.global_context
    neighbor = _get_neighbor_text(paper, section_id)

    contributions = (
        ", ".join(context.contributions)
        if context.contributions
        else "a clear methodology and measurable contribution"
    )

    body = [
        f"{sec_title} presents the core argument of this study in a formal academic tone [1].",
        f"The central problem is: {context.problem or 'an unresolved challenge in the target domain'}.",
        f"This section aligns with the paper-wide contributions: {contributions}.",
        f"The method summary is: {context.method_summary or 'a reproducible and evidence-driven approach'}.",
    ]
    if neighbor:
        body.append(f"Cross-section continuity notes: {neighbor}")
    body.append(
        "To avoid redundancy, this section prioritizes unique claims, explicit assumptions, and concise evidence framing [2]."
    )
    return "\n\n".join(body)


def _critic_rewrite(draft: str) -> tuple[str, list[str]]:
    notes: list[str] = []
    text = draft.strip()
    if not text:
        notes.append("Draft was empty; generated fallback content.")
        text = "This section provides a structured academic discussion of the proposed contribution [1]."

    if "very" in text.lower():
        notes.append("Reduced informal intensifiers for academic tone.")
        text = text.replace("very ", "")

    if "[1]" not in text:
        notes.append("Inserted pseudo-citation markers.")
        text += " [1]"
    if "[2]" not in text:
        text += " [2]"

    sentences = [s.strip() for s in text.split(".") if s.strip()]
    if len(sentences) >= 2 and sentences[0].lower() == sentences[1].lower():
        notes.append("Removed repeated opening sentence.")
        sentences.pop(1)
        text = ". ".join(sentences) + "."

    return text, notes


def generate_section_content(paper: StructuredPaper, section_id: str) -> tuple[str, list[str]]:
    draft = _compose_base_content(paper, section_id)
    return _critic_rewrite(draft)


def refine_section_content(paper: StructuredPaper, section_id: str, draft: str) -> tuple[str, list[str]]:
    _ = paper, section_id
    return _critic_rewrite(draft)
