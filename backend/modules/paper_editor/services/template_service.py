from __future__ import annotations

import shutil
import uuid
import zipfile
import json
import base64
from pathlib import Path

from modules.paper_editor.models.paper_editor_models import TemplateSectionNode


BASE_WORK_DIR = Path(__file__).resolve().parents[4] / "tmp" / "paper_editor"
BASE_WORK_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST_NAME = "template_manifest.json"


def _score_tex_candidate(path: Path) -> int:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return -1
    score = 0
    if "\\documentclass" in text:
        score += 2
    if "\\begin{document}" in text:
        score += 3
    if "\\maketitle" in text:
        score += 1
    return score


def detect_main_tex(work_dir: Path) -> Path:
    tex_files = list(work_dir.rglob("*.tex"))
    if not tex_files:
        raise ValueError("Template ZIP contains no .tex file.")
    ranked = sorted(tex_files, key=_score_tex_candidate, reverse=True)
    return ranked[0]


def create_template_workspace(zip_path: Path) -> tuple[str, Path, Path, list[str]]:
    template_id = str(uuid.uuid4())
    work_dir = BASE_WORK_DIR / template_id
    work_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(work_dir)

    main_tex = detect_main_tex(work_dir)
    files = [str(p.relative_to(work_dir)).replace("\\", "/") for p in work_dir.rglob("*") if p.is_file()]
    save_template_manifest(work_dir, main_tex)
    return template_id, work_dir, main_tex, files


def save_template_manifest(work_dir: Path, main_tex: Path, template_sections: list[TemplateSectionNode] | None = None) -> None:
    manifest = {
        "main_tex": str(main_tex.relative_to(work_dir)).replace("\\", "/"),
        "template_sections": [node.model_dump() for node in (template_sections or [])],
    }
    (work_dir / MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")


def set_injected_tex(work_dir: Path, injected_tex: Path) -> None:
    manifest_path = work_dir / MANIFEST_NAME
    manifest: dict[str, object] = {}
    if manifest_path.exists():
        try:
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                manifest = raw
        except Exception:
            manifest = {}
    manifest["injected_tex"] = str(injected_tex.relative_to(work_dir)).replace("\\", "/")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")


def resolve_main_tex(work_dir: Path) -> Path:
    manifest_path = work_dir / MANIFEST_NAME
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            rel = manifest.get("main_tex")
            if isinstance(rel, str) and rel.strip():
                candidate = (work_dir / rel).resolve()
                if candidate.exists() and str(candidate).startswith(str(work_dir.resolve())):
                    return candidate
        except Exception:
            pass
    return detect_main_tex(work_dir)


def resolve_injected_tex(work_dir: Path) -> Path | None:
    manifest_path = work_dir / MANIFEST_NAME
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            rel = manifest.get("injected_tex")
            if isinstance(rel, str) and rel.strip():
                candidate = (work_dir / rel).resolve()
                if candidate.exists() and str(candidate).startswith(str(work_dir.resolve())):
                    return candidate
        except Exception:
            pass
    candidates = sorted(work_dir.rglob("injected_main.tex"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def get_manifest_template_sections(work_dir: Path) -> list[TemplateSectionNode]:
    manifest_path = work_dir / MANIFEST_NAME
    if not manifest_path.exists():
        return []
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        raw = manifest.get("template_sections", [])
        if not isinstance(raw, list):
            return []
        out: list[TemplateSectionNode] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            out.append(TemplateSectionNode.model_validate(item))
        return out
    except Exception:
        return []


def cleanup_workspace(template_id: str) -> None:
    target = BASE_WORK_DIR / template_id
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)


def create_v2_workspace(project_name: str, files: list[dict], main_file_path: str) -> tuple[str, Path, Path]:
    template_id = f"v2-{uuid.uuid4()}"
    work_dir = BASE_WORK_DIR / template_id
    work_dir.mkdir(parents=True, exist_ok=True)
    for item in files:
        rel = str(item.get("path", "")).strip().replace("\\", "/")
        if not rel:
            continue
        target = (work_dir / rel).resolve()
        if not str(target).startswith(str(work_dir.resolve())):
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        b64 = item.get("binary_base64")
        if isinstance(b64, str) and b64:
            target.write_bytes(base64.b64decode(b64.encode("utf-8")))
        else:
            target.write_text(str(item.get("content", "")), encoding="utf-8")
    main_norm = str(main_file_path).strip().replace("\\", "/")
    main_candidate = (work_dir / main_norm).resolve()
    if not main_candidate.exists():
        tex_fallback = list(work_dir.rglob("*.tex"))
        if tex_fallback:
            main_candidate = tex_fallback[0]
        else:
            main_candidate = work_dir / "main.tex"
            main_candidate.write_text(
                "\\documentclass{article}\n\\begin{document}\nEmpty project\n\\end{document}\n",
                encoding="utf-8",
            )
    save_template_manifest(work_dir, main_candidate, template_sections=[])
    _ = project_name  # reserved for future metadata
    return template_id, work_dir, main_candidate
