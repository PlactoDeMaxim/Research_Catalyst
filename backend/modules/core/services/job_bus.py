"""
Shared async task lifecycle utility for cross-module jobs.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Awaitable, Callable
from uuid import uuid4

from modules.core.models.backbone_models import WorkspaceTask
from modules.core.services import postgres_store

_TASKS: dict[str, WorkspaceTask] = {}
_LOCK = asyncio.Lock()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def create_task(project_id: str, task_type: str, payload: dict[str, Any] | None = None) -> WorkspaceTask:
    if postgres_store.database_enabled():
        row = postgres_store.create_workspace_task(project_id=project_id, task_type=task_type, payload=payload or {})
        return WorkspaceTask(**row)
    async with _LOCK:
        task = WorkspaceTask(
            id=f"task_{uuid4().hex[:12]}",
            project_id=project_id,
            task_type=task_type,
            payload=payload or {},
        )
        _TASKS[task.id] = task
        return task


async def get_task(task_id: str) -> WorkspaceTask | None:
    if postgres_store.database_enabled():
        row = postgres_store.get_workspace_task(task_id)
        return WorkspaceTask(**row) if row else None
    async with _LOCK:
        return _TASKS.get(task_id)


async def list_tasks(project_id: str | None = None) -> list[WorkspaceTask]:
    if postgres_store.database_enabled():
        return [WorkspaceTask(**row) for row in postgres_store.list_workspace_tasks(project_id)]
    async with _LOCK:
        items = list(_TASKS.values())
    if project_id:
        items = [item for item in items if item.project_id == project_id]
    return sorted(items, key=lambda i: i.created_at, reverse=True)


async def run_task(task_id: str, runner: Callable[[], Awaitable[dict[str, Any]]]) -> WorkspaceTask | None:
    if postgres_store.database_enabled():
        task = postgres_store.get_workspace_task(task_id)
        if not task:
            return None
        postgres_store.update_workspace_task(
            task_id,
            status="running",
            attempt=int(task.get("attempt", 0)) + 1,
        )
        start = perf_counter()
        try:
            result = await runner()
            status = "succeeded"
            error_code = None
        except Exception:
            result = {}
            status = "failed"
            error_code = "runner_error"
        elapsed_ms = int((perf_counter() - start) * 1000)
        updated = postgres_store.update_workspace_task(
            task_id,
            status=status,
            result=result,
            error_code=error_code,
            duration_ms=elapsed_ms,
            attempt=int(task.get("attempt", 0)) + 1,
        )
        return WorkspaceTask(**updated) if updated else None

    async with _LOCK:
        task = _TASKS.get(task_id)
        if not task:
            return None
        task.status = "running"
        task.attempt += 1
        task.updated_at = _utc_now()
        _TASKS[task_id] = task

    start = perf_counter()
    try:
        result = await runner()
        status = "succeeded"
        error_code = None
    except Exception:
        result = {}
        status = "failed"
        error_code = "runner_error"

    elapsed_ms = int((perf_counter() - start) * 1000)
    async with _LOCK:
        task = _TASKS.get(task_id)
        if not task:
            return None
        task.status = status
        task.result = result
        task.error_code = error_code
        task.duration_ms = elapsed_ms
        task.updated_at = _utc_now()
        _TASKS[task_id] = task
        return task
