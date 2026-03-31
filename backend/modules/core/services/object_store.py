"""
Object storage abstraction.

Phase 1 uses local filesystem storage with persistent metadata written to
PostgreSQL when available. The interface is intentionally S3-friendly so a
remote backend can be swapped in later.
"""

from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any
from uuid import uuid4

from modules.core.services import postgres_store

_ROOT = Path(__file__).resolve().parents[4]
_STORE_ROOT = _ROOT / "backend" / "storage"


def _ensure_root() -> None:
    _STORE_ROOT.mkdir(parents=True, exist_ok=True)


def save_bytes(
    *,
    artifact_kind: str,
    filename: str,
    data: bytes,
    project_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _ensure_root()
    safe_name = filename.replace("\\", "_").replace("/", "_")
    rel_path = Path(artifact_kind) / f"{uuid4().hex[:12]}_{safe_name}"
    abs_path = _STORE_ROOT / rel_path
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_bytes(data)
    mime_type = mimetypes.guess_type(safe_name)[0] or "application/octet-stream"
    artifact = {
        "storage_path": str(rel_path).replace("\\", "/"),
        "artifact_kind": artifact_kind,
        "mime_type": mime_type,
        "size_bytes": len(data),
        "project_id": project_id,
        "metadata": metadata or {},
    }
    if postgres_store.database_enabled():
        artifact.update(
            postgres_store.create_object_artifact(
                storage_path=artifact["storage_path"],
                artifact_kind=artifact_kind,
                mime_type=mime_type,
                size_bytes=len(data),
                project_id=project_id,
                metadata=artifact["metadata"],
            )
        )
    return artifact


def save_text(
    *,
    artifact_kind: str,
    filename: str,
    text: str,
    project_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return save_bytes(
        artifact_kind=artifact_kind,
        filename=filename,
        data=text.encode("utf-8"),
        project_id=project_id,
        metadata=metadata,
    )


def resolve_path(storage_path: str) -> Path:
    _ensure_root()
    return _STORE_ROOT / storage_path
