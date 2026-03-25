"""
Paper Writer Service — Section-by-section academic paper generation.

Uses a 2-pass approach:
  Pass 1 — Draft each section independently with section-specific prompts
  Pass 2 — Critic pass: review each draft for redundancy, coherence, and tone

Inspired by AI-Scientist's ``perform_writeup`` module.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from modules.code_mapper.models.code_mapper_models import (
    CitationEntry,
    PaperSectionDraft,
    RepoStructure,
)
from modules.code_mapper.services import llm_client

logger = logging.getLogger(__name__)

# Standard academic paper sections with generation tips
_SECTION_SPECS: list[dict[str, str]] = [
    {
        "id": "abstract",
        "title": "Abstract",
        "tip": (
            "Write a concise 150-250 word summary. State the problem, method, "
            "key results, and significance. No citations in the abstract."
        ),
    },
    {
        "id": "introduction",
        "title": "Introduction",
        "tip": (
            "Motivate the problem, state contributions (as a numbered list), "
            "and outline the paper structure. End with a paragraph summarising "
            "the rest of the paper."
        ),
    },
    {
        "id": "related_work",
        "title": "Related Work",
        "tip": (
            "Discuss prior work in thematic groups. Compare and contrast with "
            "the current approach. Use \\cite{key} for references. "
            "Do NOT fabricate citations — use only those provided."
        ),
    },
    {
        "id": "methodology",
        "title": "Methodology",
        "tip": (
            "Describe the technical approach in detail: architecture, data pipeline, "
            "loss functions, training procedure. Use equations where appropriate. "
            "Be precise enough for reproducibility."
        ),
    },
    {
        "id": "architecture",
        "title": "System Architecture",
        "tip": (
            "Describe the high-level system design: components, data flow, "
            "class hierarchy. Reference specific modules and files from the codebase."
        ),
    },
    {
        "id": "experiments",
        "title": "Experiments",
        "tip": (
            "Describe the experimental setup: datasets, baselines, metrics, "
            "hardware. If actual results are unavailable, describe the intended "
            "evaluation protocol."
        ),
    },
    {
        "id": "results",
        "title": "Results and Discussion",
        "tip": (
            "Present findings with analysis. If actual metrics are available, "
            "report them precisely. Otherwise, describe expected outcomes based "
            "on the methodology. Discuss limitations."
        ),
    },
    {
        "id": "conclusion",
        "title": "Conclusion",
        "tip": (
            "Summarise contributions, discuss limitations, and suggest future work. "
            "Keep it concise (1-2 paragraphs)."
        ),
    },
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def generate_paper(
    repo: RepoStructure,
    citations: list[CitationEntry] | None = None,
) -> list[PaperSectionDraft]:
    """Full 2-pass paper generation pipeline."""

    citations = citations or []
    context = _build_repo_context(repo)
    cite_context = _build_citation_context(citations)

    # Pass 1: draft each section
    drafts: list[PaperSectionDraft] = []
    prev_sections: list[dict[str, str]] = []

    for spec in _SECTION_SPECS:
        draft = await _draft_section(
            spec, context, cite_context, prev_sections
        )
        drafts.append(draft)
        prev_sections.append({"title": draft.title, "content": draft.content[:500]})

    # Pass 2: critic refinement
    refined: list[PaperSectionDraft] = []
    for draft in drafts:
        improved = await _refine_section(draft, drafts, context)
        refined.append(improved)

    return refined


# ---------------------------------------------------------------------------
# Pass 1 — Drafting
# ---------------------------------------------------------------------------

async def _draft_section(
    spec: dict[str, str],
    repo_context: str,
    cite_context: str,
    prev_sections: list[dict[str, str]],
) -> PaperSectionDraft:
    prev_text = ""
    if prev_sections:
        prev_text = "\n".join(
            f"[{p['title']}]: {p['content']}" for p in prev_sections[-3:]
        )

    system = (
        "You are an expert academic writer producing a research paper from a code repository. "
        "Write in formal academic English with LaTeX formatting.\n\n"
        f"Section: {spec['title']}\n"
        f"Writing tip: {spec['tip']}\n\n"
        "Rules:\n"
        "- Use formal, third-person academic prose\n"
        "- Include \\cite{key} references where appropriate (use only provided citations)\n"
        "- Use LaTeX math notation for equations\n"
        "- No placeholder text or TODOs\n"
        "- Output ONLY the section content (no section heading, no markdown fences)"
    )

    user = (
        f"Repository context:\n{repo_context}\n\n"
        f"Available citations:\n{cite_context}\n\n"
    )
    if prev_text:
        user += f"Previous sections (for continuity):\n{prev_text}\n\n"
    user += f"Write the '{spec['title']}' section now."

    content = await llm_client.chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_tokens=3000,
        temperature=0.4,
    )

    cite_keys = _extract_cite_keys(content)
    words = len(content.split())

    return PaperSectionDraft(
        section_id=spec["id"],
        title=spec["title"],
        content=content.strip(),
        citations=cite_keys,
        word_count=words,
    )


# ---------------------------------------------------------------------------
# Pass 2 — Critic refinement
# ---------------------------------------------------------------------------

async def _refine_section(
    draft: PaperSectionDraft,
    all_drafts: list[PaperSectionDraft],
    repo_context: str,
) -> PaperSectionDraft:
    other_titles = [
        d.title for d in all_drafts if d.section_id != draft.section_id
    ]

    system = (
        "You are a rigorous academic reviewer. Improve the following paper section:\n"
        "1. Remove redundancy with other sections\n"
        "2. Strengthen academic tone and clarity\n"
        "3. Ensure technical accuracy\n"
        "4. Check citation formatting (\\cite{key})\n"
        "5. Improve transitions between paragraphs\n\n"
        "Output ONLY the improved section text."
    )

    user = (
        f"Section: {draft.title}\n\n"
        f"Draft:\n{draft.content}\n\n"
        f"Other sections in the paper: {', '.join(other_titles)}\n"
        f"Repository context (for accuracy checking):\n{repo_context[:3000]}"
    )

    refined = await llm_client.chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_tokens=3000,
        temperature=0.3,
    )

    cite_keys = _extract_cite_keys(refined)
    return PaperSectionDraft(
        section_id=draft.section_id,
        title=draft.title,
        content=refined.strip(),
        citations=cite_keys,
        word_count=len(refined.split()),
    )


# ---------------------------------------------------------------------------
# Context builders
# ---------------------------------------------------------------------------

def _build_repo_context(repo: RepoStructure) -> str:
    parts = [
        f"Repository: {repo.name}",
        f"Description: {repo.description}",
        f"Languages: {', '.join(repo.languages)}",
        f"Total files: {repo.total_files}",
    ]

    if repo.readme_content:
        parts.append(f"\nREADME:\n{repo.readme_content[:3000]}")

    if repo.classes:
        class_lines = []
        for c in repo.classes[:20]:
            bases = ", ".join(c.get("bases", []))
            methods = ", ".join(c.get("methods", [])[:8])
            class_lines.append(
                f"  - {c['name']}({bases}) in {c['file']}: methods=[{methods}]"
            )
        parts.append("\nKey classes:\n" + "\n".join(class_lines))

    if repo.functions:
        fn_lines = [
            f"  - {f['name']}({', '.join(f.get('args', []))}) in {f['file']}"
            for f in repo.functions[:20]
        ]
        parts.append("\nKey functions:\n" + "\n".join(fn_lines))

    if repo.key_files:
        file_lines = [
            f"  - {kf.path}: {kf.summary}" for kf in repo.key_files[:20] if kf.summary
        ]
        if file_lines:
            parts.append("\nFile summaries:\n" + "\n".join(file_lines))

    if repo.training_scripts:
        parts.append(f"\nTraining scripts: {', '.join(repo.training_scripts)}")

    return "\n".join(parts)[:12_000]


def _build_citation_context(citations: list[CitationEntry]) -> str:
    if not citations:
        return "No citations available yet."

    lines = []
    for c in citations[:30]:
        authors = ", ".join(c.authors[:3])
        lines.append(f"\\cite{{{c.cite_key}}} — {c.title} ({authors}, {c.year})")
    return "\n".join(lines)


def _extract_cite_keys(text: str) -> list[str]:
    import re
    keys: list[str] = []
    for m in re.finditer(r"\\cite\{([^}]+)\}", text):
        for k in m.group(1).split(","):
            k = k.strip()
            if k and k not in keys:
                keys.append(k)
    return keys
