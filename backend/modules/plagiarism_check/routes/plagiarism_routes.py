"""
Simple plagiarism-check MVP routes.

Free-source strategy:
- compare against abstracts from OpenAlex and Semantic Scholar
- score likely overlap locally
- return section-level findings and paraphrasing guidance
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from modules.core.services import object_store
from modules.plagiarism_check.models.plagiarism_models import (
    JobsListResponse,
    ModuleSettingsResponse,
    ScanAlert,
    ScanJob,
    TextScanRequest,
)
from modules.plagiarism_check.services import mvp_plagiarism_service, plagiarism_store


router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt"}
MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024


def _preview_text(value: str, max_chars: int = 220) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 1].rstrip() + "..."


@router.get("/settings", response_model=ModuleSettingsResponse)
async def settings() -> ModuleSettingsResponse:
    return ModuleSettingsResponse(
        configured=True,
        webhook_ready=True,
        backend_public_url=None,
        allowed_extensions=sorted(ALLOWED_EXTENSIONS),
    )


@router.get("/jobs", response_model=JobsListResponse)
async def list_jobs() -> JobsListResponse:
    return JobsListResponse(jobs=plagiarism_store.list_jobs())


@router.get("/jobs/{job_id}", response_model=ScanJob)
async def get_job(job_id: str) -> ScanJob:
    job = plagiarism_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Scan job not found")
    return job


@router.post("/jobs/{job_id}/refresh", response_model=ScanJob)
async def refresh_job(job_id: str) -> ScanJob:
    job = plagiarism_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Scan job not found")
    return job


@router.post("/scan/text", response_model=ScanJob)
async def scan_text(req: TextScanRequest) -> ScanJob:
    text_artifact = object_store.save_text(
        artifact_kind="plagiarism-text",
        filename=req.filename if "." in req.filename else f"{req.filename}.txt",
        text=req.text,
        metadata={"source": "text-scan"},
    )
    job = plagiarism_store.create_job(
        scan_id=str(uuid.uuid4()),
        input_type="text",
        filename=req.filename if "." in req.filename else f"{req.filename}.txt",
        text_preview=_preview_text(req.text),
        sandbox=False,
    )

    try:
        summary, findings = await mvp_plagiarism_service.analyze_text(req.text)
        updated = plagiarism_store.update_job(
            job.id,
            status="completed",
            plagiarism=summary.model_dump(),
            section_findings=[item.model_dump() for item in findings],
            alerts=[
                ScanAlert(
                    title="MVP corpus notice",
                    message="This MVP checks overlap against retrieved scholarly abstracts, not the full web or closed academic databases.",
                ).model_dump()
            ],
            scanned_document={"textArtifact": text_artifact["storage_path"]},
        )
        if not updated:
            raise HTTPException(status_code=500, detail="Failed to persist text scan job")
        return updated
    except Exception as exc:
        plagiarism_store.update_job(job.id, status="failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Text scan failed: {str(exc)}")


@router.post("/scan/file", response_model=ScanJob)
async def scan_file(
    file: UploadFile = File(...),
    sandbox: bool = Form(False),
    sensitivity_level: int = Form(3),
) -> ScanJob:
    del sandbox
    del sensitivity_level

    filename = file.filename or "upload.bin"
    suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File is too large. Max size is 15 MB.")

    upload_artifact = object_store.save_bytes(
        artifact_kind="plagiarism-upload",
        filename=filename,
        data=content,
        metadata={"source": "file-scan"},
    )

    job = plagiarism_store.create_job(
        scan_id=str(uuid.uuid4()),
        input_type="file",
        filename=filename,
        text_preview=None,
        sandbox=False,
    )

    try:
        text = mvp_plagiarism_service.extract_text_from_file(filename, content)
        if len(text.strip()) < 80:
            raise ValueError("Could not extract enough readable text from the file.")
        summary, findings = await mvp_plagiarism_service.analyze_text(text)
        updated = plagiarism_store.update_job(
            job.id,
            status="completed",
            plagiarism=summary.model_dump(),
            section_findings=[item.model_dump() for item in findings],
            scanned_document={
                "extractedTextPreview": _preview_text(text, 500),
                "uploadArtifact": upload_artifact["storage_path"],
            },
            alerts=[
                ScanAlert(
                    title="MVP corpus notice",
                    message="This MVP checks overlap against retrieved scholarly abstracts, not the full web or closed academic databases.",
                ).model_dump()
            ],
        )
        if not updated:
            raise HTTPException(status_code=500, detail="Failed to persist file scan job")
        return updated
    except Exception as exc:
        plagiarism_store.update_job(job.id, status="failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"File scan failed: {str(exc)}")
