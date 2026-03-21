from __future__ import annotations

import re
from pathlib import Path

from modules.paper_editor.models.paper_editor_models import StructuredPaper


def _escape_latex_text(text: str) -> str:
    return (
        text.replace("\\", "\\textbackslash{}")
        .replace("%", r"\%")
        .replace("_", r"\_")
        .replace("&", r"\&")
        .replace("#", r"\#")
    )


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _find_matching_section_title(
    doc_title: str,
    target_title: str,
    aliases: list[str],
) -> bool:
    dt = _normalize(doc_title)
    candidates = [_normalize(target_title)] + [_normalize(a) for a in aliases]
    return any(c and (dt == c or c in dt or dt in c) for c in candidates)


def _is_protected_section(title: str) -> bool:
    t = _normalize(title)
    protected_tokens = [
        "reference",
        "bibliography",
        "acknowledgment",
        "appendix",
        "biograph",
        "footnote",
    ]
    return any(token in t for token in protected_tokens)


def _replace_command_braced_content(src: str, command: str, replacement_text: str) -> str:
    token = f"\\{command}"
    start = src.find(token)
    if start == -1:
        return src
    brace_start = src.find("{", start)
    if brace_start == -1:
        return src

    depth = 0
    i = brace_start
    end = -1
    while i < len(src):
        ch = src[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
        i += 1

    if end == -1:
        return src
    return src[: brace_start + 1] + replacement_text + src[end:]


def _replace_environment_content(src: str, env_name: str, replacement_text: str) -> str:
    pattern = re.compile(
        rf"(\\begin\{{{re.escape(env_name)}\}})(.*?)(\\end\{{{re.escape(env_name)}\}})",
        flags=re.DOTALL,
    )
    if not pattern.search(src):
        return src
    return pattern.sub(rf"\1\n{replacement_text}\n\3", src, count=1)


def inject_into_template(
    main_tex_path: Path,
    paper: StructuredPaper,
    section_aliases: dict[str, list[str]],
    section_targets: dict[str, str] | None = None,
) -> tuple[Path, str, dict[str, list[str]]]:
    src = main_tex_path.read_text(encoding="utf-8", errors="ignore")

    # title
    if paper.title:
        src = _replace_command_braced_content(src, "title", _escape_latex_text(paper.title))

    # author
    if paper.authors:
        author_text = ", ".join(paper.authors)
        src = _replace_command_braced_content(src, "author", _escape_latex_text(author_text))

    # abstract
    abstract_sec = next((s for s in paper.sections if s.id.lower() == "abstract" or s.title.lower() == "abstract"), None)
    if abstract_sec:
        src = _replace_environment_content(src, "abstract", _escape_latex_text(abstract_sec.content))

    impact_sec = next(
        (
            s
            for s in paper.sections
            if s.id.lower() in {"impact", "impact-statement", "impact_statement"}
            or "impact" in s.title.lower()
        ),
        None,
    )
    if "\\begin{IEEEImpStatement}" in src:
        src = _replace_environment_content(
            src,
            "IEEEImpStatement",
            _escape_latex_text(impact_sec.content if impact_sec else ""),
        )

    keywords_sec = next(
        (
            s
            for s in paper.sections
            if s.id.lower() in {"keywords", "keyword"}
            or "keyword" in s.title.lower()
        ),
        None,
    )
    if "\\begin{IEEEkeywords}" in src:
        src = _replace_environment_content(
            src,
            "IEEEkeywords",
            _escape_latex_text(keywords_sec.content if keywords_sec else ""),
        )

    # section body replacement
    section_pattern = re.compile(
        r"(\\section\*?\{(?P<title>[^}]+)\}\s*)(?P<body>.*?)(?=(\\section\*?\{|\\end\{document\}))",
        flags=re.DOTALL,
    )
    matches = list(section_pattern.finditer(src))
    replaced_ids: set[str] = set()
    replaced_match_indexes: set[int] = set()
    matched_details: list[str] = []
    out = src
    offset = 0
    target_map = section_targets or {}

    # Pass 0: explicit target mapping by template node title/path
    for match_index, match in enumerate(matches):
        doc_title = match.group("title")
        if _is_protected_section(doc_title):
            continue
        for sec in paper.sections:
            if sec.id in replaced_ids or sec.title.lower() == "abstract":
                continue
            explicit = target_map.get(sec.id, "")
            if not explicit:
                continue
            if _normalize(doc_title) != _normalize(explicit):
                continue
            start = match.start("body") + offset
            end = match.end("body") + offset
            replacement = _escape_latex_text(sec.content).strip() + "\n\n"
            out = out[:start] + replacement + out[end:]
            offset += len(replacement) - (end - start)
            replaced_ids.add(sec.id)
            replaced_match_indexes.add(match_index)
            matched_details.append(f"{sec.title} -> {doc_title} (explicit-target)")
            break

    # Pass 1: strict title/alias matching
    for match_index, match in enumerate(matches):
        doc_title = match.group("title")
        if _is_protected_section(doc_title):
            continue
        for sec in paper.sections:
            if sec.id in replaced_ids or sec.title.lower() == "abstract":
                continue
            aliases = section_aliases.get(sec.id, [])
            if _find_matching_section_title(doc_title, sec.title, aliases):
                start = match.start("body") + offset
                end = match.end("body") + offset
                replacement = _escape_latex_text(sec.content).strip() + "\n\n"
                out = out[:start] + replacement + out[end:]
                offset += len(replacement) - (end - start)
                replaced_ids.add(sec.id)
                replaced_match_indexes.add(match_index)
                matched_details.append(f"{sec.title} -> {doc_title} (alias/title)")
                break

    # Pass 2: ordered fallback mapping for remaining non-empty sections
    remaining_sections = [
        s
        for s in paper.sections
        if s.id not in replaced_ids
        and s.title.lower() != "abstract"
        and (s.content or "").strip()
    ]
    for match_index, match in enumerate(matches):
        if not remaining_sections:
            break
        if match_index in replaced_match_indexes:
            continue
        doc_title = match.group("title")
        if _is_protected_section(doc_title):
            continue
        sec = remaining_sections.pop(0)
        start = match.start("body") + offset
        end = match.end("body") + offset
        replacement = _escape_latex_text(sec.content).strip() + "\n\n"
        out = out[:start] + replacement + out[end:]
        offset += len(replacement) - (end - start)
        replaced_ids.add(sec.id)
        replaced_match_indexes.add(match_index)
        matched_details.append(f"{sec.title} -> {doc_title} (ordered-fallback)")

    # Remaining missing sections -> append before end document (only for non-empty content)
    appended_sections: list[str] = []
    missing = [
        s
        for s in paper.sections
        if s.id not in replaced_ids and s.title.lower() != "abstract" and (s.content or "").strip()
    ]
    if missing and "\\end{document}" in out:
        insertion = ""
        for sec in missing:
            insertion += f"\\section{{{_escape_latex_text(sec.title)}}}\n{_escape_latex_text(sec.content)}\n\n"
            appended_sections.append(sec.title)
        out = out.replace("\\end{document}", insertion + "\\end{document}", 1)

    injected_path = main_tex_path.parent / "injected_main.tex"
    injected_path.write_text(out, encoding="utf-8")
    matched = [s.title for s in paper.sections if s.id in replaced_ids]
    skipped_details: list[str] = []
    skipped: list[str] = []
    for sec in paper.sections:
        if sec.title.lower() == "abstract":
            continue
        content = (sec.content or "").strip()
        if sec.id in replaced_ids or sec.title in appended_sections:
            continue
        if not content:
            skipped.append(sec.title)
            skipped_details.append(f"{sec.title}: empty content")
            continue
        skipped.append(sec.title)
        skipped_details.append(f"{sec.title}: no writable insertion point found")

    return injected_path, out[:1200], {
        "matched_sections": matched,
        "skipped_sections": skipped,
        "appended_sections": appended_sections,
        "matched_details": matched_details,
        "skipped_details": skipped_details,
    }
