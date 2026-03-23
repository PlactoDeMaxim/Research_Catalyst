"""
Local persistence for plagiarism scan jobs.

This keeps the UI responsive while provider-side plagiarism and AI checks are
polled asynchronously.
"""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from modules.plagiarism_check.models.plagiarism_models import ScanJob


_ROOT = Path(__file__).resolve().parents[4]
_DATA_DIR = _ROOT / "backend" / "data"
_STORE_PATH = _DATA_DIR / "plagiarism_jobs.json"
_LOCK = threading.RLock()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_store() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not _STORE_PATH.exists():
        _STORE_PATH.write_text("{}", encoding="utf-8")


def _load_all() -> dict[str, Any]:
    _ensure_store()
    try:
        raw = json.loads(_STORE_PATH.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def _save_all(data: dict[str, Any]) -> None:
    _ensure_store()
    _STORE_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=True), encoding="utf-8")


def create_job(
    *,
    scan_id: str,
    input_type: str,
    filename: str,
    text_preview: str | None,
    sandbox: bool,
) -> ScanJob:
    with _LOCK:
        now = _utc_now()
        job = ScanJob(
            id=str(uuid.uuid4()),
            scan_id=scan_id,
            status="submitting",
            input_type=input_type,
            filename=filename,
            created_at=now,
            updated_at=now,
            sandbox=sandbox,
            text_preview=text_preview,
        )
        data = _load_all()
        data[job.id] = job.model_dump()
        _save_all(data)
        return job


def list_jobs() -> list[ScanJob]:
    with _LOCK:
        data = _load_all()
        jobs = [ScanJob.model_validate(item) for item in data.values()]
        return sorted(jobs, key=lambda item: item.created_at, reverse=True)


def get_job(job_id: str) -> ScanJob | None:
    with _LOCK:
        data = _load_all()
        item = data.get(job_id)
        if not item:
            return None
        return ScanJob.model_validate(item)


def get_job_by_scan_id(scan_id: str) -> ScanJob | None:
    with _LOCK:
        data = _load_all()
        for item in data.values():
            if item.get("scan_id") == scan_id:
                return ScanJob.model_validate(item)
        return None


def update_job(job_id: str, **updates: Any) -> ScanJob | None:
    with _LOCK:
        data = _load_all()
        item = data.get(job_id)
        if not item:
            return None
        merged = {**item, **updates, "updated_at": _utc_now()}
        job = ScanJob.model_validate(merged)
        data[job_id] = job.model_dump()
        _save_all(data)
        return job


def update_job_by_scan_id(scan_id: str, **updates: Any) -> ScanJob | None:
    with _LOCK:
        data = _load_all()
        target_id = None
        target_item = None
        for job_id, item in data.items():
            if item.get("scan_id") == scan_id:
                target_id = job_id
                target_item = item
                break
        if not target_id or not target_item:
            return None
        merged = {**target_item, **updates, "updated_at": _utc_now()}
        job = ScanJob.model_validate(merged)
        data[target_id] = job.model_dump()
        _save_all(data)
        return job
