"""
Paper Writer Service — Single-call project report generation.

Generates all report sections in ONE LLM call as structured JSON,
replacing the previous 2-pass (draft + critic) approach that consumed
~16 LLM calls per paper.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from modules.code_mapper.models.code_mapper_models import (
    PaperSectionDraft,
    RepoStructure,
)
from modules.code_mapper.services import llm_client

logger = logging.getLogger(__name__)

# Report sections to generate
_REPORT_SECTIONS = [
    {
        "id": "abstract",
        "title": "Abstract",
        "instruction": (
            "Write a concise 150-250 word summary. State the problem the project solves, "
            "the approach/method used, key features, and significance."
        ),
    },
    {
        "id": "introduction",
        "title": "Introduction",
        "instruction": (
            "Motivate the problem, explain why this project exists, state the main "
            "contributions as a numbered list, and outline the rest of the report."
        ),
    },
    {
        "id": "methodology",
        "title": "Methodology",
        "instruction": (
            "Describe the technical approach in detail: algorithms, data flow, "
            "key design decisions, and any frameworks/libraries used. "
            "Be precise enough for reproducibility."
        ),
    },
    {
        "id": "architecture",
        "title": "System Architecture",
        "instruction": (
            "Describe the high-level system design: components, modules, data flow, "
            "class hierarchy. Reference specific files and modules from the codebase."
        ),
    },
    {
        "id": "results",
        "title": "Results and Discussion",
        "instruction": (
            "Discuss what the project achieves, its strengths, limitations, "
            "and any performance characteristics. If actual metrics are unavailable, "
            "describe expected outcomes based on the methodology."
        ),
    },
    {
        "id": "conclusion",
        "title": "Conclusion",
        "instruction": (
            "Summarise contributions, discuss limitations, and suggest future work. "
            "Keep it concise (1-2 paragraphs)."
        ),
    },
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def generate_report(repo: RepoStructure) -> list[PaperSectionDraft]:
    """Generate all report sections in a single LLM call.

    Returns a list of PaperSectionDraft objects with editable content.
    """

    context = _build_repo_context(repo)
    sections_spec = json.dumps(
        [{"id": s["id"], "title": s["title"], "instruction": s["instruction"]}
         for s in _REPORT_SECTIONS],
        indent=2,
    )

    system = (
        "You are an expert technical writer. Generate a complete project report "
        "from the repository analysis provided below.\n\n"
        "Rules:\n"
        "- Write in formal, clear, third-person technical prose\n"
        "- Be specific — reference actual files, classes, and functions from the codebase\n"
        "- No placeholder text, no TODOs, no fabricated information\n"
        "- Each section should be substantial (at least 150 words)\n"
        "- Use plain text, no LaTeX or markdown formatting\n\n"
        "You MUST respond with a JSON object containing a 'sections' array.\n"
        "Each element must have: 'id' (string), 'title' (string), 'content' (string).\n"
        "Generate content for ALL of the following sections:\n\n"
        f"{sections_spec}"
    )

    user = f"Repository analysis:\n\n{context}"

    try:
        result = await llm_client.chat_json(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=4096,
            temperature=0.4,
        )

        raw_sections = result.get("sections", [])
        if not isinstance(raw_sections, list):
            raise ValueError(f"Expected 'sections' array, got: {type(raw_sections)}")

        drafts: list[PaperSectionDraft] = []
        generated_ids = {s.get("id") for s in raw_sections if isinstance(s, dict)}

        for spec in _REPORT_SECTIONS:
            # Find matching section in LLM response
            match = next(
                (s for s in raw_sections
                 if isinstance(s, dict) and s.get("id") == spec["id"]),
                None,
            )
            content = ""
            if match:
                content = str(match.get("content", "")).strip()

            if not content:
                content = f"[This section needs to be written: {spec['instruction']}]"

            drafts.append(PaperSectionDraft(
                section_id=spec["id"],
                title=spec["title"],
                content=content,
                citations=[],
                word_count=len(content.split()),
            ))

        return drafts

    except Exception as exc:
        logger.error("Report generation failed: %s", exc)
        # Return skeleton sections so the user can still edit
        return [
            PaperSectionDraft(
                section_id=spec["id"],
                title=spec["title"],
                content=f"[Generation failed. Please write this section manually: {spec['instruction']}]",
                citations=[],
                word_count=0,
            )
            for spec in _REPORT_SECTIONS
        ]


# ---------------------------------------------------------------------------
# Context builder
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

    return "\n".join(parts)[:10_000]
