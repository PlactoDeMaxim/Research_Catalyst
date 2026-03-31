"""
Code Mapper Routes — FastAPI endpoints for both features.

Feature 1: Paper-to-Code (POST upload, GET status/stream/result/download)
Feature 2: Repo-to-Paper (POST analyze, GET status/stream/result/download)
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from modules.code_mapper.models.code_mapper_models import (
    JobPhase,
    JobStatus,
    PaperSectionDraft,
    PaperToCodeResult,
    PaperUploadResponse,
    RepoAnalyzeRequest,
    RepoAnalyzeResponse,
    RepoToPaperResult,
    SectionsUpdateRequest,
)
from modules.code_mapper.services import job_manager

router = APIRouter()


class TestLLMRequest(BaseModel):
    prompt: str


@router.post("/test-llm")
async def test_llm(req: TestLLMRequest):
    """Quick endpoint to verify the configured LLM provider works."""
    from modules.code_mapper.services import llm_client

    system_instruction = (
        "You are a helpful research assistant. Please provide a clear and concise answer. "
        "You must keep your response under 5000 words and ensure you finish your thoughts completely "
        "so that the response does not get cut off."
    )

    text = await llm_client.chat(
        [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": req.prompt}
        ],
        temperature=0.2,
    )
    return {"text": text}


# ═══════════════════════════════════════════════════════════════════════════
# Feature 1 — Paper-to-Code
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/paper-to-code/upload", response_model=PaperUploadResponse)
async def upload_paper(file: UploadFile = File(...)):
    """Upload a research paper (PDF or Word) and start the code generation pipeline."""

    filename = (file.filename or "").lower()
    if not filename.endswith((".pdf", ".docx", ".doc")):
        raise HTTPException(
            status_code=400,
            detail="Only PDF and Word (.docx) files are supported.",
        )

    with tempfile.NamedTemporaryFile(
        delete=False, suffix=Path(filename).suffix, prefix="cm_upload_"
    ) as tmp:
        data = await file.read()
        tmp.write(data)
        tmp_path = Path(tmp.name)

    job = job_manager.create_job()
    await job_manager.run_in_background(
        job.job_id,
        lambda jid: _paper_to_code_pipeline(jid, tmp_path),
    )

    return PaperUploadResponse(job_id=job.job_id)


@router.get("/paper-to-code/status/{job_id}", response_model=JobStatus)
async def paper_to_code_status(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@router.get("/paper-to-code/stream/{job_id}")
async def paper_to_code_stream(job_id: str):
    """SSE stream for real-time progress updates."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return StreamingResponse(
        job_manager.sse_generator(job_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/paper-to-code/result/{job_id}")
async def paper_to_code_result(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.phase not in (JobPhase.COMPLETED, JobPhase.FAILED):
        raise HTTPException(status_code=202, detail="Job still in progress.")
    return job.result or {}


@router.get("/paper-to-code/download/{job_id}")
async def paper_to_code_download(job_id: str):
    """Download the generated project as a ZIP file."""
    from modules.code_mapper.services.packager_service import get_package_path

    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.phase != JobPhase.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed yet.")

    zip_path = get_package_path(job_id)
    if not zip_path or not zip_path.exists():
        raise HTTPException(status_code=404, detail="Package not found.")

    return FileResponse(
        str(zip_path),
        media_type="application/zip",
        filename=zip_path.name,
        content_disposition_type="attachment",
    )


# ═══════════════════════════════════════════════════════════════════════════
# Feature 2 — Repo-to-Paper (Simplified: Editable Project Report)
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/repo-to-paper/analyze", response_model=RepoAnalyzeResponse)
async def analyze_repo(req: RepoAnalyzeRequest):
    """Submit a GitHub repository URL and start the report generation pipeline."""

    if not req.github_url.strip():
        raise HTTPException(status_code=400, detail="GitHub URL is required.")

    job = job_manager.create_job()
    await job_manager.run_in_background(
        job.job_id,
        lambda jid: _repo_to_paper_pipeline(jid, req),
    )

    return RepoAnalyzeResponse(job_id=job.job_id)


@router.get("/repo-to-paper/status/{job_id}", response_model=JobStatus)
async def repo_to_paper_status(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@router.get("/repo-to-paper/stream/{job_id}")
async def repo_to_paper_stream(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return StreamingResponse(
        job_manager.sse_generator(job_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/repo-to-paper/result/{job_id}")
async def repo_to_paper_result(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.phase not in (JobPhase.COMPLETED, JobPhase.FAILED):
        raise HTTPException(status_code=202, detail="Job still in progress.")
    return job.result or {}


@router.put("/repo-to-paper/sections/{job_id}")
async def update_sections(job_id: str, req: SectionsUpdateRequest):
    """Receive edited sections from frontend, re-export LaTeX/Word, update job result."""
    from modules.code_mapper.services.export_service import export_latex, export_word

    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.phase != JobPhase.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed yet.")

    # Rebuild sections from the update
    sections = [
        PaperSectionDraft(
            section_id=s.section_id,
            title=s.title,
            content=s.content,
            citations=[],
            word_count=len(s.content.split()),
        )
        for s in req.sections
    ]

    # Get the existing result to retrieve repo structure
    existing_result = job.result or {}
    from modules.code_mapper.models.code_mapper_models import RepoStructure
    repo = RepoStructure(**existing_result.get("repo_structure", {"name": "project"}))

    # Re-export
    output_formats = existing_result.get("output_formats", ["latex", "word"])
    latex_path = None
    word_path = None

    if "latex" in output_formats:
        latex_dir = export_latex(
            repo, sections, [], "", job_id,
            existing_result.get("paper_style", "generic"),
        )
        latex_path = str(latex_dir / "main.tex")

    if "word" in output_formats:
        word_file = export_word(repo, sections, [], job_id)
        word_path = str(word_file)

    # Update job result
    result = RepoToPaperResult(
        repo_structure=repo,
        sections=sections,
        citations=[],
        bibtex_content="",
        latex_path=latex_path,
        word_path=word_path,
    )

    updated_result = result.model_dump(mode="json")
    updated_result["output_formats"] = output_formats
    updated_result["paper_style"] = existing_result.get("paper_style", "generic")

    job_manager.update_job(
        job_id,
        phase=JobPhase.COMPLETED,
        progress=100.0,
        message="Report updated and re-exported!",
        result=updated_result,
    )

    return {"status": "ok", "message": "Sections updated and re-exported."}


@router.get("/repo-to-paper/download/{job_id}")
async def repo_to_paper_download(
    job_id: str,
    format: str = Query("latex", regex="^(latex|word)$"),
):
    """Download the generated paper as LaTeX or Word."""
    from modules.code_mapper.services.export_service import get_latex_dir, get_word_path

    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.phase != JobPhase.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed yet.")

    if format == "word":
        doc_path = get_word_path(job_id)
        if not doc_path or not doc_path.exists():
            raise HTTPException(status_code=404, detail="Word document not found.")
        return FileResponse(
            str(doc_path),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=doc_path.name,
            content_disposition_type="attachment",
        )

    latex_dir = get_latex_dir(job_id)
    if not latex_dir or not latex_dir.exists():
        raise HTTPException(status_code=404, detail="LaTeX output not found.")

    import zipfile
    import tempfile as _tf

    zip_path = Path(_tf.mktemp(suffix=".zip", prefix="cm_latex_"))
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in latex_dir.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(latex_dir))

    return FileResponse(
        str(zip_path),
        media_type="application/zip",
        filename="paper_latex.zip",
        content_disposition_type="attachment",
    )


# ═══════════════════════════════════════════════════════════════════════════
# Pipeline orchestration
# ═══════════════════════════════════════════════════════════════════════════

async def _paper_to_code_pipeline(job_id: str, file_path: Path) -> None:
    """Full Paper-to-Code pipeline: parse → extract → blueprint → generate → validate → package."""

    from modules.code_mapper.services.paper_parser_service import parse_document
    from modules.code_mapper.services.method_extractor_service import extract_methodology
    from modules.code_mapper.services.code_generator_service import (
        generate_blueprint,
        generate_all_files,
    )
    from modules.code_mapper.services.code_validator_service import validate_and_fix
    from modules.code_mapper.services.packager_service import package_project

    # Step 1: Parse
    job_manager.update_job(
        job_id, phase=JobPhase.PARSING, progress=5.0, message="Parsing document…"
    )
    doc = parse_document(file_path)

    # Step 2: Extract methodology
    job_manager.update_job(
        job_id, phase=JobPhase.EXTRACTING, progress=15.0,
        message="Extracting methodology and architecture…",
    )
    methodology = await extract_methodology(doc)

    # Step 3: Generate blueprint
    job_manager.update_job(
        job_id, phase=JobPhase.GENERATING, progress=30.0,
        message="Generating code blueprint…",
    )
    blueprint = await generate_blueprint(methodology)

    # Step 4: Generate all files
    job_manager.update_job(
        job_id, phase=JobPhase.GENERATING, progress=45.0,
        message=f"Generating {len(blueprint.files)} source files…",
    )
    files = await generate_all_files(blueprint, methodology)

    # Step 5: Validate and fix
    job_manager.update_job(
        job_id, phase=JobPhase.VALIDATING, progress=70.0,
        message="Validating generated code…",
    )
    files, validation = await validate_and_fix(files)

    # Step 6: Package
    job_manager.update_job(
        job_id, phase=JobPhase.PACKAGING, progress=90.0,
        message="Packaging project as ZIP…",
    )
    zip_path = package_project(blueprint, files, job_id)

    result = PaperToCodeResult(
        methodology=methodology,
        blueprint=blueprint,
        files=files,
        validation=validation,
        zip_path=str(zip_path),
    )

    job_manager.update_job(
        job_id,
        phase=JobPhase.COMPLETED,
        progress=100.0,
        message="Code generation complete!",
        artifact_path=str(zip_path),
        result=result.model_dump(mode="json"),
    )

    # Cleanup temp upload
    try:
        file_path.unlink(missing_ok=True)
    except Exception:
        pass


async def _repo_to_paper_pipeline(job_id: str, req: RepoAnalyzeRequest) -> None:
    """Simplified Repo-to-Paper pipeline: clone → analyze → write → export.

    Reduced from 6 stages to 3. No citation discovery, no multi-round injection,
    no 2-pass refinement. Single LLM call for report generation.
    """

    from modules.code_mapper.services.repo_analyzer_service import analyze_repo
    from modules.code_mapper.services.paper_writer_service import generate_report
    from modules.code_mapper.services.export_service import export_latex, export_word

    # Step 1: Clone & analyze
    job_manager.update_job(
        job_id, phase=JobPhase.ANALYZING, progress=10.0,
        message="Cloning and analyzing repository…",
    )
    repo = await analyze_repo(req.github_url, job_id)

    # Step 2: Generate report (single LLM call)
    job_manager.update_job(
        job_id, phase=JobPhase.GENERATING, progress=40.0,
        message="Writing report sections…",
    )
    sections = await generate_report(repo)

    # Step 3: Export
    job_manager.update_job(
        job_id, phase=JobPhase.EXPORTING, progress=80.0,
        message="Exporting report…",
    )

    latex_path = None
    word_path = None

    if "latex" in req.output_formats:
        latex_dir = export_latex(
            repo, sections, [], "", job_id, req.paper_style
        )
        latex_path = str(latex_dir / "main.tex")

    if "word" in req.output_formats:
        word_file = export_word(repo, sections, [], job_id)
        word_path = str(word_file)

    result = RepoToPaperResult(
        repo_structure=repo,
        sections=sections,
        citations=[],
        bibtex_content="",
        latex_path=latex_path,
        word_path=word_path,
    )

    result_dict = result.model_dump(mode="json")
    # Store output_formats and paper_style so sections update endpoint can re-export
    result_dict["output_formats"] = req.output_formats
    result_dict["paper_style"] = req.paper_style

    job_manager.update_job(
        job_id,
        phase=JobPhase.COMPLETED,
        progress=100.0,
        message="Report generation complete!",
        result=result_dict,
    )
