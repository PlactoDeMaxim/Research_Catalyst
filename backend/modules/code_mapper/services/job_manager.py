"""
Async job manager for long-running Code Mapper pipelines.

Provides:
  - In-memory job store with thread-safe access
  - ``run_in_background`` to kick off a coroutine as a fire-and-forget task
  - ``sse_generator`` for Server-Sent Events progress streaming
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from threading import Lock
from typing import Any, AsyncGenerator, Callable, Coroutine, Optional

from modules.code_mapper.models.code_mapper_models import JobPhase, JobStatus

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------

_JOBS: dict[str, JobStatus] = {}
_LOCK = Lock()
_EVENTS: dict[str, asyncio.Queue[Optional[dict[str, Any]]]] = {}


def create_job() -> JobStatus:
    job_id = uuid.uuid4().hex[:12]
    job = JobStatus(job_id=job_id, phase=JobPhase.QUEUED, message="Queued")
    with _LOCK:
        _JOBS[job_id] = job
        _EVENTS[job_id] = asyncio.Queue()
    return job


def get_job(job_id: str) -> Optional[JobStatus]:
    with _LOCK:
        return _JOBS.get(job_id)


def update_job(
    job_id: str,
    *,
    phase: JobPhase | None = None,
    progress: float | None = None,
    message: str | None = None,
    artifact_path: str | None = None,
    error: str | None = None,
    result: dict[str, Any] | None = None,
) -> JobStatus:
    """Update a job and push an SSE event to any listening clients."""

    with _LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            raise KeyError(f"Unknown job: {job_id}")

        if phase is not None:
            job.phase = phase
        if progress is not None:
            job.progress = progress
        if message is not None:
            job.message = message
        if artifact_path is not None:
            job.artifact_path = artifact_path
        if error is not None:
            job.error = error
        if result is not None:
            job.result = result

        _JOBS[job_id] = job

        event_q = _EVENTS.get(job_id)

    if event_q is not None:
        event_data = job.model_dump(mode="json")
        try:
            event_q.put_nowait(event_data)
        except asyncio.QueueFull:
            pass

    return job


# ---------------------------------------------------------------------------
# Background task runner
# ---------------------------------------------------------------------------

async def run_in_background(
    job_id: str,
    coro_fn: Callable[[str], Coroutine[Any, Any, None]],
) -> None:
    """Schedule *coro_fn(job_id)* as a background asyncio task.

    The coroutine is expected to call ``update_job`` to push progress.
    On unhandled exceptions the job is marked FAILED automatically.
    """

    async def _wrapper() -> None:
        try:
            await coro_fn(job_id)
        except Exception as exc:
            logger.exception("Background job %s failed", job_id)
            update_job(
                job_id,
                phase=JobPhase.FAILED,
                progress=0.0,
                message="Pipeline failed",
                error=str(exc),
            )
        finally:
            q = _EVENTS.get(job_id)
            if q is not None:
                try:
                    q.put_nowait(None)
                except asyncio.QueueFull:
                    pass

    asyncio.create_task(_wrapper())


# ---------------------------------------------------------------------------
# SSE generator
# ---------------------------------------------------------------------------

async def sse_generator(job_id: str) -> AsyncGenerator[str, None]:
    """Yield ``text/event-stream`` formatted events for a given job.

    Terminates when the job reaches a terminal phase (COMPLETED / FAILED)
    or after the sentinel ``None`` is pushed onto the queue.
    """

    q = _EVENTS.get(job_id)
    if q is None:
        yield _sse_format({"error": "unknown job_id"}, event="error")
        return

    while True:
        try:
            data = await asyncio.wait_for(q.get(), timeout=30.0)
        except asyncio.TimeoutError:
            yield _sse_format({}, event="ping")
            continue

        if data is None:
            job = get_job(job_id)
            if job:
                yield _sse_format(job.model_dump(mode="json"), event="done")
            return

        yield _sse_format(data, event="progress")

        phase = data.get("phase", "")
        if phase in (JobPhase.COMPLETED.value, JobPhase.FAILED.value):
            return


def _sse_format(data: dict[str, Any], *, event: str = "message") -> str:
    import json
    payload = json.dumps(data, default=str)
    return f"event: {event}\ndata: {payload}\n\n"
