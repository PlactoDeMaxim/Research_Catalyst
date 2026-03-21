from __future__ import annotations

import re
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from modules.paper_editor.models.paper_editor_models import (
    CompilePreflightResponse,
    CompileJobResponse,
    CompileRequest,
    V2CompileJobResponse,
    V2CompileSourceRequest,
    GenerateSectionRequest,
    GeneratedSectionResponse,
    InjectRequest,
    InjectResponse,
    JobStatusResponse,
    RefineSectionRequest,
    StructureUpdateRequest,
    StructureUpdateResponse,
    UploadTemplateResponse,
)
from modules.paper_editor.services.compile_service import enqueue_compile_job, get_compile_preflight
from modules.paper_editor.services.generation_service import (
    generate_section_content,
    refine_section_content,
)
from modules.paper_editor.services.injection_service import inject_into_template
from modules.paper_editor.services.job_store import get_job
from modules.paper_editor.services.structure_service import (
    extract_template_sections,
    infer_constraints_from_template,
    validate_structure,
)
from modules.paper_editor.services.template_service import (
    BASE_WORK_DIR,
    create_v2_workspace,
    create_template_workspace,
    save_template_manifest,
    set_injected_tex,
    resolve_injected_tex,
    resolve_main_tex,
)


router = APIRouter()


_LATEX_DIAG_RE = re.compile(r"(?P<file>[^\s:]+\.tex):(?P<line>\d+):\s+(?P<message>.+)")
_L_LINE_RE = re.compile(r"^l\.(?P<line>\d+)\s+(?P<message>.+)$", re.MULTILINE)


def _extract_diagnostics(logs: list[str]) -> list[dict[str, object]]:
    """Parse common pdflatex / latexmk log patterns into structured diagnostics."""
    text = "\n".join(logs[-80:])
    diagnostics: list[dict[str, object]] = []
    for match in _LATEX_DIAG_RE.finditer(text):
        diagnostics.append(
            {
                "file": match.group("file").strip().lstrip("./"),
                "line": int(match.group("line")),
                "message": match.group("message").strip(),
                "severity": "error",
            }
        )
    for match in _L_LINE_RE.finditer(text):
        diagnostics.append(
            {
                "file": "compiled_input.tex",
                "line": int(match.group("line")),
                "message": match.group("message").strip(),
                "severity": "error",
            }
        )
    seen: set[tuple[str, int, str]] = set()
    unique: list[dict[str, object]] = []
    for d in diagnostics:
        key = (str(d.get("file", "")), int(d.get("line", 0)), str(d.get("message", "")))
        if key in seen:
            continue
        seen.add(key)
        unique.append(d)
    return unique[-50:]


@router.post("/generate-section", response_model=GeneratedSectionResponse)
async def generate_section(req: GenerateSectionRequest):
    content, notes = generate_section_content(req.paper, req.section_id)
    return GeneratedSectionResponse(section_id=req.section_id, content=content, critic_notes=notes)


@router.post("/refine-section", response_model=GeneratedSectionResponse)
async def refine_section(req: RefineSectionRequest):
    content, notes = refine_section_content(req.paper, req.section_id, req.draft)
    return GeneratedSectionResponse(section_id=req.section_id, content=content, critic_notes=notes)


@router.post("/update-structure", response_model=StructureUpdateResponse)
async def update_structure(req: StructureUpdateRequest):
    return validate_structure(req.sections, req.constraints)


@router.post("/upload-template", response_model=UploadTemplateResponse)
async def upload_template(file: UploadFile = File(...)):
    filename = file.filename or ""
    if not filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only ZIP upload is supported in MVP.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        data = await file.read()
        tmp.write(data)
        temp_path = Path(tmp.name)

    try:
        template_id, _, main_tex, files = create_template_workspace(temp_path)
        content = main_tex.read_text(encoding="utf-8", errors="ignore")
        constraints = infer_constraints_from_template(content)
        template_sections = extract_template_sections(content)
        save_template_manifest(BASE_WORK_DIR / template_id, main_tex, template_sections)
        return UploadTemplateResponse(
            template_id=template_id,
            main_tex=str(main_tex.relative_to(BASE_WORK_DIR / template_id)).replace("\\", "/"),
            constraints=constraints,
            files=files,
            template_sections=template_sections,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Template upload failed: {exc}") from exc
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)


@router.post("/inject", response_model=InjectResponse)
async def inject_template(req: InjectRequest):
    work_dir = BASE_WORK_DIR / req.template_id
    if not work_dir.exists():
        raise HTTPException(status_code=404, detail="Template workspace not found.")

    try:
        main_tex = resolve_main_tex(work_dir)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unable to locate main .tex file: {exc}") from exc

    injected_path, snippet, diagnostics = inject_into_template(main_tex, req.paper, req.section_aliases, req.section_targets)
    set_injected_tex(work_dir, injected_path)
    injected_source = injected_path.read_text(encoding="utf-8", errors="ignore")
    return InjectResponse(
        template_id=req.template_id,
        tex_path=str(injected_path),
        preview_snippet=snippet,
        injected_source=injected_source,
        main_tex_path=str(main_tex),
        matched_sections=diagnostics.get("matched_sections", []),
        skipped_sections=diagnostics.get("skipped_sections", []),
        appended_sections=diagnostics.get("appended_sections", []),
        matched_details=diagnostics.get("matched_details", []),
        skipped_details=diagnostics.get("skipped_details", []),
    )


@router.post("/compile", response_model=CompileJobResponse)
async def compile_template(req: CompileRequest):
    work_dir = BASE_WORK_DIR / req.template_id
    tex_path = resolve_injected_tex(work_dir)
    if not tex_path:
        raise HTTPException(status_code=400, detail="Inject step required before compile.")

    job = enqueue_compile_job(req.template_id, tex_path, req.max_retries)
    return CompileJobResponse(job_id=job.job_id, status=job.status, message=job.message)


@router.post("/v2/compile-source", response_model=V2CompileJobResponse)
async def compile_source_v2(req: V2CompileSourceRequest):
    payload_files = [f.model_dump() for f in req.files]
    template_id, _, main_tex = create_v2_workspace(req.project_name, payload_files, req.main_file_path)
    job = enqueue_compile_job(template_id, main_tex, req.max_retries)
    return V2CompileJobResponse(
        template_id=template_id,
        job_id=job.job_id,
        status=job.status,
        message=job.message,
    )


@router.get("/preflight/{template_id}", response_model=CompilePreflightResponse)
async def compile_preflight(template_id: str):
    work_dir = BASE_WORK_DIR / template_id
    if not work_dir.exists():
        raise HTTPException(status_code=404, detail="Template workspace not found.")
    data = get_compile_preflight(template_id)
    return CompilePreflightResponse(**data)


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    job.diagnostics = _extract_diagnostics(job.logs)
    return job


@router.get("/download/{job_id}")
async def download_job_artifact(job_id: str, download: bool = False):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if not job.artifact_path:
        raise HTTPException(status_code=400, detail="No artifact available.")
    path = Path(job.artifact_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Artifact not found.")
    if path.suffix.lower() == ".pdf":
        return FileResponse(
            str(path),
            media_type="application/pdf",
            filename=path.name,
            content_disposition_type="attachment" if download else "inline",
        )
    return FileResponse(
        str(path),
        media_type="application/x-tex",
        filename=path.name,
        content_disposition_type="attachment",
    )
