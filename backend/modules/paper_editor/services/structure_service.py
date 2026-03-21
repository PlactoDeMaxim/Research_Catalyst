from __future__ import annotations

import re

from modules.paper_editor.models.paper_editor_models import (
    PaperSection,
    TemplateSectionNode,
    TemplateConstraints,
    StructureUpdateResponse,
)


def infer_constraints_from_template(main_tex: str) -> TemplateConstraints:
    low = main_tex.lower()
    strict = "\\documentclass[conference]" in low or "ieeetran" in low or "acmart" in low
    required = ["abstract", "introduction", "conclusion"] if strict else ["abstract"]
    return TemplateConstraints(
        strict_mode=strict,
        required_sections=required,
        allowed_extra_sections=not strict,
        section_order_fixed=strict,
    )


def extract_template_sections(main_tex: str) -> list[TemplateSectionNode]:
    nodes: list[TemplateSectionNode] = []
    order = 0

    def add_node(
        node_id: str,
        title: str,
        level: int,
        latex_command: str,
        editable: bool = True,
        protected: bool = False,
    ) -> None:
        nonlocal order
        order += 1
        nodes.append(
            TemplateSectionNode(
                id=node_id,
                title=title,
                level=level,
                latex_command=latex_command,
                editable=editable,
                protected=protected,
                order=order,
            )
        )

    # Front-matter blocks (if present in template)
    if re.search(r"\\title\s*\{", main_tex):
        add_node("title", "Title", 0, "title", editable=True)
    if re.search(r"\\author\s*\{", main_tex):
        add_node("authors", "Authors", 0, "author", editable=True)
    if re.search(r"\\begin\{abstract\}", main_tex):
        add_node("abstract", "Abstract", 0, "abstract", editable=True)
    if re.search(r"\\begin\{IEEEkeywords\}", main_tex):
        add_node("keywords", "Keywords", 0, "keywords", editable=True)
    if re.search(r"\\begin\{IEEEImpStatement\}", main_tex):
        add_node("impact", "Impact Statement", 0, "impact", editable=True)

    protected_tokens = ("reference", "bibliograph", "acknowledg", "appendix")
    heading_pattern = re.compile(
        r"\\(?P<cmd>section|subsection|subsubsection)\*?\{(?P<title>[^}]+)\}",
        flags=re.IGNORECASE,
    )

    used_ids: set[str] = {n.id for n in nodes}
    for match in heading_pattern.finditer(main_tex):
        cmd = match.group("cmd").lower()
        title = match.group("title").strip()
        if not title:
            continue
        normalized = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or f"{cmd}-{order+1}"
        node_id = normalized
        suffix = 2
        while node_id in used_ids:
            node_id = f"{normalized}-{suffix}"
            suffix += 1
        used_ids.add(node_id)
        protected = any(tok in title.lower() for tok in protected_tokens)
        level = 1 if cmd == "section" else 2 if cmd == "subsection" else 3
        add_node(node_id, title, level, cmd, editable=not protected, protected=protected)

    return nodes


def validate_structure(
    sections: list[PaperSection],
    constraints: TemplateConstraints,
) -> StructureUpdateResponse:
    errors: list[str] = []
    normalized = [PaperSection(id=s.id, title=s.title.strip() or s.id, content=s.content) for s in sections]

    ids = [s.id.lower() for s in normalized]
    title_index = {s.title.lower(): i for i, s in enumerate(normalized)}

    for required in constraints.required_sections:
        req_low = required.lower()
        if req_low not in ids and req_low not in title_index:
            errors.append(f"Missing required section: {required}")

    if constraints.section_order_fixed:
        fixed_order = ["abstract", "introduction", "related work", "methodology", "results", "conclusion"]
        present = [s.title.lower() for s in normalized]
        last_idx = -1
        for label in fixed_order:
            if label in present:
                idx = present.index(label)
                if idx < last_idx:
                    errors.append("Section order violates fixed template sequence.")
                    break
                last_idx = idx

    if not constraints.allowed_extra_sections:
        allowed = {x.lower() for x in constraints.required_sections}
        for section in normalized:
            if section.id.lower() not in allowed and section.title.lower() not in allowed:
                errors.append(f"Extra section not allowed in strict mode: {section.title}")

    return StructureUpdateResponse(
        valid=len(errors) == 0,
        errors=errors,
        normalized_sections=normalized,
    )
