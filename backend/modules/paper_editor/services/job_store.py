from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Optional

from modules.paper_editor.models.paper_editor_models import JobStatusResponse
from modules.paper_editor.services.template_service import BASE_WORK_DIR


_JOBS: dict[str, JobStatusResponse] = {}
_LOCK = Lock()
_JOB_DIR = BASE_WORK_DIR / "_job_store"
_JOB_DIR.mkdir(parents=True, exist_ok=True)


def _job_path(job_id: str) -> Path:
    return _JOB_DIR / f"{job_id}.json"


def _persist_job(job: JobStatusResponse) -> None:
    _job_path(job.job_id).write_text(json.dumps(job.model_dump()), encoding="utf-8")


def _load_persisted_job(job_id: str) -> Optional[JobStatusResponse]:
    path = _job_path(job_id)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return JobStatusResponse.model_validate(data)
    except Exception:
        return None


def create_job(job_id: str) -> JobStatusResponse:
    job = JobStatusResponse(job_id=job_id, status="queued", message="Queued")
    with _LOCK:
        _JOBS[job_id] = job
        _persist_job(job)
    return job


def get_job(job_id: str) -> Optional[JobStatusResponse]:
    with _LOCK:
        in_mem = _JOBS.get(job_id)
        if in_mem is not None:
            return in_mem
        persisted = _load_persisted_job(job_id)
        if persisted is not None:
            _JOBS[job_id] = persisted
            return persisted
        return None


def save_job(job: JobStatusResponse) -> None:
    with _LOCK:
        _JOBS[job.job_id] = job
        _persist_job(job)
