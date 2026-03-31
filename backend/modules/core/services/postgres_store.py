"""
PostgreSQL-backed persistence for the Phase 1 shared backbone.

This module keeps runtime persistence available to the Python backend while the
Prisma schema remains the source of truth for the relational model.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Iterable, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import uuid4

try:
    from psycopg import connect
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover - optional dependency during import
    connect = None
    dict_row = None


_BOOTSTRAPPED = False
_LOCK = threading.RLock()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def database_enabled() -> bool:
    return bool(os.getenv("DATABASE_URL")) and connect is not None


def _connection_dsn() -> str:
    """
    Normalize Prisma-style DATABASE_URL for psycopg.

    Prisma accepts ?schema=public in DATABASE_URL, while psycopg rejects the
    unknown "schema" query parameter. We strip it for psycopg connections.

    Adds connect_timeout (seconds) if missing so unreachable hosts fail fast instead of
    hanging for the default libpq timeout (common when DATABASE_URL is set but Postgres is down).
    Override with PG_CONNECT_TIMEOUT or ?connect_timeout= in DATABASE_URL.
    """
    raw = os.environ["DATABASE_URL"]
    parts = urlsplit(raw)
    query_items = parse_qsl(parts.query, keep_blank_values=True)
    filtered = [(k, v) for (k, v) in query_items if k.lower() != "schema"]
    keys_lower = {k.lower() for k, _ in filtered}
    if "connect_timeout" not in keys_lower:
        filtered.append(("connect_timeout", os.getenv("PG_CONNECT_TIMEOUT", "8")))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(filtered), parts.fragment))


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Unsupported JSON type: {type(value)!r}")


def _serialize(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, default=_json_default)


def _normalize_row(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    normalized: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, datetime):
            normalized[key] = value.isoformat()
        else:
            normalized[key] = value
    return normalized


def _fetchall(query: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
    ensure_phase1_schema()
    assert connect is not None and dict_row is not None
    with connect(_connection_dsn(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(query, tuple(params))
            return [_normalize_row(row) or {} for row in cur.fetchall()]


def _fetchone(query: str, params: Iterable[Any] = ()) -> dict[str, Any] | None:
    ensure_phase1_schema()
    assert connect is not None and dict_row is not None
    with connect(_connection_dsn(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(query, tuple(params))
            row = cur.fetchone()
            return _normalize_row(row)


def _execute(query: str, params: Iterable[Any] = ()) -> None:
    ensure_phase1_schema()
    assert connect is not None
    with connect(_connection_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(query, tuple(params))
        conn.commit()


def ensure_phase1_schema() -> bool:
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED or not database_enabled():
        return _BOOTSTRAPPED

    with _LOCK:
        if _BOOTSTRAPPED or not database_enabled():
            return _BOOTSTRAPPED

        ddl = """
        CREATE TABLE IF NOT EXISTS rc_workspace_projects (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            kind TEXT NOT NULL DEFAULT 'general',
            status TEXT NOT NULL DEFAULT 'PLANNING',
            topic TEXT NOT NULL DEFAULT '',
            domain TEXT NOT NULL DEFAULT 'general',
            deadline TEXT NOT NULL DEFAULT '',
            owner_id TEXT NOT NULL DEFAULT 'local-user',
            storage_key TEXT NOT NULL DEFAULT '',
            editor_state JSONB,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_rc_workspace_projects_kind ON rc_workspace_projects(kind);

        CREATE TABLE IF NOT EXISTS rc_workspace_milestones (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES rc_workspace_projects(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            due_date TEXT NOT NULL DEFAULT '',
            completed BOOLEAN NOT NULL DEFAULT FALSE,
            phase TEXT NOT NULL DEFAULT '',
            ordering INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_rc_workspace_milestones_project_id ON rc_workspace_milestones(project_id);

        CREATE TABLE IF NOT EXISTS rc_workspace_citations (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES rc_workspace_projects(id) ON DELETE CASCADE,
            citation_text TEXT NOT NULL,
            csl_json TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_rc_workspace_citations_project_id ON rc_workspace_citations(project_id);

        CREATE TABLE IF NOT EXISTS rc_plagiarism_jobs (
            id TEXT PRIMARY KEY,
            scan_id TEXT NOT NULL UNIQUE,
            project_id TEXT,
            status TEXT NOT NULL,
            input_type TEXT NOT NULL,
            filename TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            payload JSONB NOT NULL DEFAULT '{}'::jsonb
        );
        CREATE INDEX IF NOT EXISTS idx_rc_plagiarism_jobs_scan_id ON rc_plagiarism_jobs(scan_id);

        CREATE TABLE IF NOT EXISTS rc_workspace_tasks (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            task_type TEXT NOT NULL,
            status TEXT NOT NULL,
            attempt INTEGER NOT NULL DEFAULT 0,
            duration_ms INTEGER NOT NULL DEFAULT 0,
            payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            result JSONB NOT NULL DEFAULT '{}'::jsonb,
            error_code TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_rc_workspace_tasks_project_id ON rc_workspace_tasks(project_id);

        CREATE TABLE IF NOT EXISTS rc_workspace_documents (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            title TEXT NOT NULL,
            source_type TEXT NOT NULL DEFAULT 'upload',
            mime_type TEXT NOT NULL DEFAULT 'text/plain',
            location TEXT NOT NULL DEFAULT '',
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_rc_workspace_documents_project_id ON rc_workspace_documents(project_id);

        CREATE TABLE IF NOT EXISTS rc_workspace_evidence_chunks (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            document_id TEXT NOT NULL,
            content TEXT NOT NULL,
            tokens INTEGER NOT NULL DEFAULT 0,
            chunk_index INTEGER NOT NULL DEFAULT 0,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            embedding DOUBLE PRECISION[],
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_rc_workspace_evidence_project_id ON rc_workspace_evidence_chunks(project_id);
        CREATE INDEX IF NOT EXISTS idx_rc_workspace_evidence_document_id ON rc_workspace_evidence_chunks(document_id);

        CREATE TABLE IF NOT EXISTS rc_workspace_claims (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            text TEXT NOT NULL,
            source_document_id TEXT,
            evidence_chunk_ids TEXT[] NOT NULL DEFAULT '{}',
            citation_ids TEXT[] NOT NULL DEFAULT '{}',
            confidence DOUBLE PRECISION NOT NULL DEFAULT 0.0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_rc_workspace_claims_project_id ON rc_workspace_claims(project_id);

        CREATE TABLE IF NOT EXISTS rc_verification_tasks (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            target_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'queued',
            result JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_rc_verification_tasks_project_id ON rc_verification_tasks(project_id);

        CREATE TABLE IF NOT EXISTS rc_prompt_templates (
            id TEXT PRIMARY KEY,
            task_type TEXT NOT NULL,
            title TEXT NOT NULL,
            system_prompt TEXT NOT NULL,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS rc_object_artifacts (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            storage_path TEXT NOT NULL,
            artifact_kind TEXT NOT NULL,
            mime_type TEXT NOT NULL DEFAULT 'application/octet-stream',
            size_bytes BIGINT NOT NULL DEFAULT 0,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS rc_literature_collections (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            tags TEXT[] NOT NULL DEFAULT '{}',
            papers JSONB NOT NULL DEFAULT '[]'::jsonb,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_rc_literature_collections_project_id ON rc_literature_collections(project_id);

        CREATE TABLE IF NOT EXISTS rc_screening_sessions (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            title TEXT NOT NULL,
            query TEXT NOT NULL DEFAULT '',
            inclusion_criteria TEXT NOT NULL DEFAULT '',
            exclusion_criteria TEXT NOT NULL DEFAULT '',
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_rc_screening_sessions_project_id ON rc_screening_sessions(project_id);

        CREATE TABLE IF NOT EXISTS rc_screening_entries (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES rc_screening_sessions(id) ON DELETE CASCADE,
            paper_id TEXT NOT NULL,
            title TEXT NOT NULL,
            decision TEXT NOT NULL DEFAULT 'unreviewed',
            reason TEXT NOT NULL DEFAULT '',
            tags TEXT[] NOT NULL DEFAULT '{}',
            paper JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_rc_screening_entries_session_id ON rc_screening_entries(session_id);
        """

        assert connect is not None
        with connect(_connection_dsn()) as conn:
            with conn.cursor() as cur:
                cur.execute(ddl)
            conn.commit()

        _BOOTSTRAPPED = True
        return True


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:16]}"


def list_workspace_projects(kind: str | None = None) -> list[dict[str, Any]]:
    if kind:
        return _fetchall(
            "SELECT * FROM rc_workspace_projects WHERE kind = %s ORDER BY updated_at DESC",
            (kind,),
        )
    return _fetchall("SELECT * FROM rc_workspace_projects ORDER BY updated_at DESC")


def get_workspace_project(project_id: str) -> dict[str, Any] | None:
    return _fetchone("SELECT * FROM rc_workspace_projects WHERE id = %s", (project_id,))


def create_workspace_project(
    *,
    title: str,
    description: str = "",
    kind: str = "general",
    status: str = "PLANNING",
    topic: str = "",
    domain: str = "general",
    deadline: str = "",
    owner_id: str = "local-user",
    storage_key: str = "",
    editor_state: Any = None,
    metadata: dict[str, Any] | None = None,
    project_id: str | None = None,
) -> dict[str, Any]:
    now = _utc_now()
    row_id = project_id or _new_id("proj")
    _execute(
        """
        INSERT INTO rc_workspace_projects
        (id, title, description, kind, status, topic, domain, deadline, owner_id, storage_key, editor_state, metadata, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s)
        """,
        (
            row_id,
            title,
            description,
            kind,
            status,
            topic,
            domain,
            deadline,
            owner_id,
            storage_key,
            _serialize(editor_state),
            _serialize(metadata or {}),
            now,
            now,
        ),
    )
    return get_workspace_project(row_id) or {}


def update_workspace_project(project_id: str, **fields: Any) -> dict[str, Any] | None:
    current = get_workspace_project(project_id)
    if not current:
        return None

    def _field_or_current(name: str, fallback: Any) -> Any:
        value = fields.get(name, fallback)
        return fallback if value is None else value

    merged = {
        "title": _field_or_current("title", current["title"]),
        "description": _field_or_current("description", current.get("description", "")),
        "kind": _field_or_current("kind", current.get("kind", "general")),
        "status": _field_or_current("status", current.get("status", "PLANNING")),
        "topic": _field_or_current("topic", current.get("topic", "")),
        "domain": _field_or_current("domain", current.get("domain", "general")),
        "deadline": _field_or_current("deadline", current.get("deadline", "")),
        "owner_id": _field_or_current("owner_id", current.get("owner_id", "local-user")),
        "storage_key": _field_or_current("storage_key", current.get("storage_key", "")),
        "editor_state": fields.get("editor_state", current.get("editor_state")),
        "metadata": _field_or_current("metadata", current.get("metadata") or {}),
        "updated_at": _field_or_current("updated_at", _utc_now()),
    }
    _execute(
        """
        UPDATE rc_workspace_projects
        SET title = %s,
            description = %s,
            kind = %s,
            status = %s,
            topic = %s,
            domain = %s,
            deadline = %s,
            owner_id = %s,
            storage_key = %s,
            editor_state = %s::jsonb,
            metadata = %s::jsonb,
            updated_at = %s
        WHERE id = %s
        """,
        (
            merged["title"],
            merged["description"],
            merged["kind"],
            merged["status"],
            merged["topic"],
            merged["domain"],
            merged["deadline"],
            merged["owner_id"],
            merged["storage_key"],
            _serialize(merged["editor_state"]),
            _serialize(merged["metadata"]),
            merged["updated_at"],
            project_id,
        ),
    )
    return get_workspace_project(project_id)


def delete_workspace_project(project_id: str) -> bool:
    current = get_workspace_project(project_id)
    if not current:
        return False
    _execute("DELETE FROM rc_workspace_projects WHERE id = %s", (project_id,))
    return True


def list_workspace_milestones(project_id: str) -> list[dict[str, Any]]:
    return _fetchall(
        """
        SELECT * FROM rc_workspace_milestones
        WHERE project_id = %s
        ORDER BY ordering ASC, created_at ASC
        """,
        (project_id,),
    )


def create_workspace_milestone(
    *,
    project_id: str,
    title: str,
    description: str = "",
    due_date: str = "",
    completed: bool = False,
    phase: str = "",
    order: int = 0,
    milestone_id: str | None = None,
) -> dict[str, Any]:
    now = _utc_now()
    row_id = milestone_id or _new_id("ms")
    _execute(
        """
        INSERT INTO rc_workspace_milestones
        (id, project_id, title, description, due_date, completed, phase, ordering, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (row_id, project_id, title, description, due_date, completed, phase, order, now, now),
    )
    return _fetchone("SELECT * FROM rc_workspace_milestones WHERE id = %s", (row_id,)) or {}


def update_workspace_milestone(milestone_id: str, **fields: Any) -> dict[str, Any] | None:
    current = _fetchone("SELECT * FROM rc_workspace_milestones WHERE id = %s", (milestone_id,))
    if not current:
        return None
    title = current["title"] if fields.get("title") is None else fields.get("title")
    description = current.get("description", "") if fields.get("description") is None else fields.get("description")
    due_date = current.get("due_date", "") if fields.get("due_date") is None else fields.get("due_date")
    completed = current.get("completed", False) if fields.get("completed") is None else fields.get("completed")
    phase = current.get("phase", "") if fields.get("phase") is None else fields.get("phase")
    order = current.get("ordering", 0) if fields.get("order") is None else fields.get("order")
    _execute(
        """
        UPDATE rc_workspace_milestones
        SET title = %s,
            description = %s,
            due_date = %s,
            completed = %s,
            phase = %s,
            ordering = %s,
            updated_at = %s
        WHERE id = %s
        """,
        (
            title,
            description,
            due_date,
            completed,
            phase,
            order,
            _utc_now(),
            milestone_id,
        ),
    )
    return _fetchone("SELECT * FROM rc_workspace_milestones WHERE id = %s", (milestone_id,))


def delete_workspace_milestone(milestone_id: str) -> bool:
    current = _fetchone("SELECT * FROM rc_workspace_milestones WHERE id = %s", (milestone_id,))
    if not current:
        return False
    _execute("DELETE FROM rc_workspace_milestones WHERE id = %s", (milestone_id,))
    return True


def replace_workspace_milestones(project_id: str, milestones: list[dict[str, Any]]) -> None:
    _execute("DELETE FROM rc_workspace_milestones WHERE project_id = %s", (project_id,))
    for idx, item in enumerate(milestones):
        create_workspace_milestone(
            project_id=project_id,
            title=str(item.get("title", "")),
            description=str(item.get("description", "")),
            due_date=str(item.get("due_date", "")),
            completed=bool(item.get("completed", False)),
            phase=str(item.get("phase", "")),
            order=int(item.get("order", idx)),
            milestone_id=str(item.get("id") or _new_id("ms")),
        )


def list_workspace_citations(project_id: str) -> list[dict[str, Any]]:
    return _fetchall(
        "SELECT * FROM rc_workspace_citations WHERE project_id = %s ORDER BY created_at DESC",
        (project_id,),
    )


def create_workspace_citation(
    *, project_id: str, citation_text: str, csl_json: str = "", citation_id: str | None = None
) -> dict[str, Any]:
    row_id = citation_id or _new_id("cite")
    _execute(
        """
        INSERT INTO rc_workspace_citations (id, project_id, citation_text, csl_json)
        VALUES (%s, %s, %s, %s)
        """,
        (row_id, project_id, citation_text, csl_json),
    )
    return _fetchone("SELECT * FROM rc_workspace_citations WHERE id = %s", (row_id,)) or {}


def delete_workspace_citation(citation_id: str) -> bool:
    current = _fetchone("SELECT * FROM rc_workspace_citations WHERE id = %s", (citation_id,))
    if not current:
        return False
    _execute("DELETE FROM rc_workspace_citations WHERE id = %s", (citation_id,))
    return True


def create_plagiarism_job(*, scan_id: str, input_type: str, filename: str, payload: dict[str, Any], project_id: str | None = None) -> dict[str, Any]:
    row_id = str(payload.get("id") or _new_id("plag"))
    _execute(
        """
        INSERT INTO rc_plagiarism_jobs
        (id, scan_id, project_id, status, input_type, filename, created_at, updated_at, payload)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
        """,
        (
            row_id,
            scan_id,
            project_id,
            payload.get("status", "submitting"),
            input_type,
            filename,
            payload.get("created_at", _utc_now()),
            payload.get("updated_at", _utc_now()),
            _serialize(payload),
        ),
    )
    return get_plagiarism_job(row_id) or {}


def list_plagiarism_jobs() -> list[dict[str, Any]]:
    rows = _fetchall("SELECT * FROM rc_plagiarism_jobs ORDER BY created_at DESC")
    return [row.get("payload", {}) for row in rows]


def get_plagiarism_job(job_id: str) -> dict[str, Any] | None:
    row = _fetchone("SELECT * FROM rc_plagiarism_jobs WHERE id = %s", (job_id,))
    return row.get("payload") if row else None


def get_plagiarism_job_by_scan_id(scan_id: str) -> dict[str, Any] | None:
    row = _fetchone("SELECT * FROM rc_plagiarism_jobs WHERE scan_id = %s", (scan_id,))
    return row.get("payload") if row else None


def update_plagiarism_job(job_id: str, **updates: Any) -> dict[str, Any] | None:
    current = _fetchone("SELECT * FROM rc_plagiarism_jobs WHERE id = %s", (job_id,))
    if not current:
        return None
    payload = current.get("payload") or {}
    payload.update(updates)
    payload["updated_at"] = _utc_now()
    _execute(
        """
        UPDATE rc_plagiarism_jobs
        SET status = %s, filename = %s, updated_at = %s, payload = %s::jsonb
        WHERE id = %s
        """,
        (
            payload.get("status", current.get("status", "submitting")),
            payload.get("filename", current.get("filename", "")),
            payload["updated_at"],
            _serialize(payload),
            job_id,
        ),
    )
    return get_plagiarism_job(job_id)


def create_workspace_task(*, project_id: str, task_type: str, payload: dict[str, Any] | None = None, task_id: str | None = None) -> dict[str, Any]:
    row_id = task_id or _new_id("task")
    _execute(
        """
        INSERT INTO rc_workspace_tasks
        (id, project_id, task_type, status, payload, result)
        VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb)
        """,
        (row_id, project_id, task_type, "queued", _serialize(payload or {}), _serialize({})),
    )
    return get_workspace_task(row_id) or {}


def get_workspace_task(task_id: str) -> dict[str, Any] | None:
    return _fetchone("SELECT * FROM rc_workspace_tasks WHERE id = %s", (task_id,))


def list_workspace_tasks(project_id: str | None = None) -> list[dict[str, Any]]:
    if project_id:
        return _fetchall(
            "SELECT * FROM rc_workspace_tasks WHERE project_id = %s ORDER BY created_at DESC",
            (project_id,),
        )
    return _fetchall("SELECT * FROM rc_workspace_tasks ORDER BY created_at DESC")


def update_workspace_task(task_id: str, **updates: Any) -> dict[str, Any] | None:
    current = get_workspace_task(task_id)
    if not current:
        return None
    _execute(
        """
        UPDATE rc_workspace_tasks
        SET status = %s,
            attempt = %s,
            duration_ms = %s,
            payload = %s::jsonb,
            result = %s::jsonb,
            error_code = %s,
            updated_at = %s
        WHERE id = %s
        """,
        (
            updates.get("status", current.get("status", "queued")),
            updates.get("attempt", current.get("attempt", 0)),
            updates.get("duration_ms", current.get("duration_ms", 0)),
            _serialize(updates.get("payload", current.get("payload") or {})),
            _serialize(updates.get("result", current.get("result") or {})),
            updates.get("error_code", current.get("error_code")),
            _utc_now(),
            task_id,
        ),
    )
    return get_workspace_task(task_id)


def create_document(
    *,
    project_id: str,
    title: str,
    source_type: str = "upload",
    mime_type: str = "text/plain",
    location: str = "",
    metadata: dict[str, Any] | None = None,
    document_id: str | None = None,
) -> dict[str, Any]:
    row_id = document_id or _new_id("doc")
    _execute(
        """
        INSERT INTO rc_workspace_documents
        (id, project_id, title, source_type, mime_type, location, metadata)
        VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
        """,
        (row_id, project_id, title, source_type, mime_type, location, _serialize(metadata or {})),
    )
    return _fetchone("SELECT * FROM rc_workspace_documents WHERE id = %s", (row_id,)) or {}


def list_documents(project_id: str) -> list[dict[str, Any]]:
    return _fetchall(
        "SELECT * FROM rc_workspace_documents WHERE project_id = %s ORDER BY created_at DESC",
        (project_id,),
    )


def create_evidence_chunk(
    *,
    project_id: str,
    document_id: str,
    content: str,
    tokens: int,
    chunk_index: int,
    metadata: dict[str, Any] | None = None,
    embedding: list[float] | None = None,
    chunk_id: str | None = None,
) -> dict[str, Any]:
    row_id = chunk_id or _new_id("ev")
    _execute(
        """
        INSERT INTO rc_workspace_evidence_chunks
        (id, project_id, document_id, content, tokens, chunk_index, metadata, embedding)
        VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
        """,
        (row_id, project_id, document_id, content, tokens, chunk_index, _serialize(metadata or {}), embedding),
    )
    return _fetchone("SELECT * FROM rc_workspace_evidence_chunks WHERE id = %s", (row_id,)) or {}


def list_evidence_chunks(project_id: str, document_id: str | None = None) -> list[dict[str, Any]]:
    if document_id:
        return _fetchall(
            """
            SELECT * FROM rc_workspace_evidence_chunks
            WHERE project_id = %s AND document_id = %s
            ORDER BY chunk_index ASC
            """,
            (project_id, document_id),
        )
    return _fetchall(
        """
        SELECT * FROM rc_workspace_evidence_chunks
        WHERE project_id = %s
        ORDER BY created_at DESC
        """,
        (project_id,),
    )


def create_claim(
    *,
    project_id: str,
    text: str,
    source_document_id: str | None = None,
    evidence_chunk_ids: list[str] | None = None,
    citation_ids: list[str] | None = None,
    confidence: float = 0.0,
    claim_id: str | None = None,
) -> dict[str, Any]:
    row_id = claim_id or _new_id("claim")
    _execute(
        """
        INSERT INTO rc_workspace_claims
        (id, project_id, text, source_document_id, evidence_chunk_ids, citation_ids, confidence)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            row_id,
            project_id,
            text,
            source_document_id,
            evidence_chunk_ids or [],
            citation_ids or [],
            confidence,
        ),
    )
    return _fetchone("SELECT * FROM rc_workspace_claims WHERE id = %s", (row_id,)) or {}


def list_claims(project_id: str) -> list[dict[str, Any]]:
    return _fetchall(
        "SELECT * FROM rc_workspace_claims WHERE project_id = %s ORDER BY created_at DESC",
        (project_id,),
    )


def create_prompt_template(
    *,
    task_type: str,
    title: str,
    system_prompt: str,
    metadata: dict[str, Any] | None = None,
    template_id: str | None = None,
) -> dict[str, Any]:
    row_id = template_id or _new_id("prompt")
    _execute(
        """
        INSERT INTO rc_prompt_templates
        (id, task_type, title, system_prompt, metadata)
        VALUES (%s, %s, %s, %s, %s::jsonb)
        ON CONFLICT (id) DO UPDATE
        SET task_type = EXCLUDED.task_type,
            title = EXCLUDED.title,
            system_prompt = EXCLUDED.system_prompt,
            metadata = EXCLUDED.metadata,
            updated_at = NOW()
        """,
        (row_id, task_type, title, system_prompt, _serialize(metadata or {})),
    )
    return _fetchone("SELECT * FROM rc_prompt_templates WHERE id = %s", (row_id,)) or {}


def list_prompt_templates(task_type: str | None = None) -> list[dict[str, Any]]:
    if task_type:
        return _fetchall(
            "SELECT * FROM rc_prompt_templates WHERE task_type = %s ORDER BY updated_at DESC",
            (task_type,),
        )
    return _fetchall("SELECT * FROM rc_prompt_templates ORDER BY updated_at DESC")


def create_object_artifact(
    *,
    storage_path: str,
    artifact_kind: str,
    mime_type: str = "application/octet-stream",
    size_bytes: int = 0,
    project_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    artifact_id: str | None = None,
) -> dict[str, Any]:
    row_id = artifact_id or _new_id("obj")
    _execute(
        """
        INSERT INTO rc_object_artifacts
        (id, project_id, storage_path, artifact_kind, mime_type, size_bytes, metadata)
        VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
        """,
        (row_id, project_id, storage_path, artifact_kind, mime_type, size_bytes, _serialize(metadata or {})),
    )
    return _fetchone("SELECT * FROM rc_object_artifacts WHERE id = %s", (row_id,)) or {}


def create_literature_collection(
    *,
    title: str,
    description: str = "",
    tags: list[str] | None = None,
    papers: list[dict[str, Any]] | None = None,
    metadata: dict[str, Any] | None = None,
    project_id: str | None = None,
    collection_id: str | None = None,
) -> dict[str, Any]:
    row_id = collection_id or _new_id("col")
    now = _utc_now()
    _execute(
        """
        INSERT INTO rc_literature_collections
        (id, project_id, title, description, tags, papers, metadata, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s)
        """,
        (
            row_id,
            project_id,
            title,
            description,
            tags or [],
            _serialize(papers or []),
            _serialize(metadata or {}),
            now,
            now,
        ),
    )
    return _fetchone("SELECT * FROM rc_literature_collections WHERE id = %s", (row_id,)) or {}


def list_literature_collections(project_id: str | None = None) -> list[dict[str, Any]]:
    if project_id:
        return _fetchall(
            "SELECT * FROM rc_literature_collections WHERE project_id = %s ORDER BY updated_at DESC",
            (project_id,),
        )
    return _fetchall("SELECT * FROM rc_literature_collections ORDER BY updated_at DESC")


def create_screening_session(
    *,
    title: str,
    query: str = "",
    inclusion_criteria: str = "",
    exclusion_criteria: str = "",
    metadata: dict[str, Any] | None = None,
    project_id: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    row_id = session_id or _new_id("screen")
    now = _utc_now()
    _execute(
        """
        INSERT INTO rc_screening_sessions
        (id, project_id, title, query, inclusion_criteria, exclusion_criteria, metadata, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
        """,
        (
            row_id,
            project_id,
            title,
            query,
            inclusion_criteria,
            exclusion_criteria,
            _serialize(metadata or {}),
            now,
            now,
        ),
    )
    return _fetchone("SELECT * FROM rc_screening_sessions WHERE id = %s", (row_id,)) or {}


def get_screening_session(session_id: str) -> dict[str, Any] | None:
    return _fetchone("SELECT * FROM rc_screening_sessions WHERE id = %s", (session_id,))


def list_screening_sessions(project_id: str | None = None) -> list[dict[str, Any]]:
    if project_id:
        return _fetchall(
            "SELECT * FROM rc_screening_sessions WHERE project_id = %s ORDER BY updated_at DESC",
            (project_id,),
        )
    return _fetchall("SELECT * FROM rc_screening_sessions ORDER BY updated_at DESC")


def upsert_screening_entry(
    *,
    session_id: str,
    paper_id: str,
    title: str,
    decision: str,
    reason: str = "",
    tags: list[str] | None = None,
    paper: dict[str, Any] | None = None,
    entry_id: str | None = None,
) -> dict[str, Any]:
    existing = _fetchone(
        "SELECT * FROM rc_screening_entries WHERE session_id = %s AND paper_id = %s",
        (session_id, paper_id),
    )
    now = _utc_now()
    if existing:
        _execute(
            """
            UPDATE rc_screening_entries
            SET title = %s,
                decision = %s,
                reason = %s,
                tags = %s,
                paper = %s::jsonb,
                updated_at = %s
            WHERE id = %s
            """,
            (
                title,
                decision,
                reason,
                tags or [],
                _serialize(paper or {}),
                now,
                existing["id"],
            ),
        )
        return _fetchone("SELECT * FROM rc_screening_entries WHERE id = %s", (existing["id"],)) or {}

    row_id = entry_id or _new_id("entry")
    _execute(
        """
        INSERT INTO rc_screening_entries
        (id, session_id, paper_id, title, decision, reason, tags, paper, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
        """,
        (row_id, session_id, paper_id, title, decision, reason, tags or [], _serialize(paper or {}), now, now),
    )
    return _fetchone("SELECT * FROM rc_screening_entries WHERE id = %s", (row_id,)) or {}


def list_screening_entries(session_id: str) -> list[dict[str, Any]]:
    return _fetchall(
        "SELECT * FROM rc_screening_entries WHERE session_id = %s ORDER BY updated_at DESC",
        (session_id,),
    )
