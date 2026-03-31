"""
multi_research_routes.py — FastAPI routes for the Multi-Agent Research pipeline.

Endpoints:
  POST /api/multi-research/run      — SSE streaming endpoint
  POST /api/multi-research/run-sync — Synchronous fallback
"""

import asyncio
import json
import logging
import traceback

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from modules.multi_research.services.pipeline import run_research_pipeline

logger = logging.getLogger(__name__)
router = APIRouter()


class ResearchRequest(BaseModel):
    topic: str = Field(..., min_length=1, description="Research topic to investigate")


class ResearchResponse(BaseModel):
    topic: str
    report: str
    status: str = "completed"


# ── SSE Streaming Endpoint ──────────────────────────────────────────────────

@router.post("/run")
async def run_research_sse(request: ResearchRequest):
    """Run the multi-agent research pipeline with SSE progress events."""

    async def event_generator():
        topic = request.topic.strip()
        q = asyncio.Queue()
        loop = asyncio.get_event_loop()

        def sync_callback(evt_dict):
            loop.call_soon_threadsafe(q.put_nowait, evt_dict)

        def worker():
            try:
                report = run_research_pipeline(topic, progress_callback=sync_callback)
                loop.call_soon_threadsafe(q.put_nowait, {"event": "complete", "report": report})
            except Exception as e:
                logger.error("Pipeline failed: %s", traceback.format_exc())
                loop.call_soon_threadsafe(q.put_nowait, {"event": "error", "message": str(e)})

        # Send initial event
        yield {
            "event": "step",
            "data": json.dumps({
                "step": "start",
                "status": "running",
                "message": f"Starting multi-agent research for: {topic}",
            }),
        }

        import threading
        t = threading.Thread(target=worker)
        t.start()

        while True:
            msg = await q.get()
            if msg.get("event") == "complete":
                yield {
                    "event": "complete",
                    "data": json.dumps({
                        "step": "complete",
                        "status": "completed",
                        "report": msg["report"],
                        "topic": topic,
                    }),
                }
                break
            elif msg.get("event") == "error":
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "step": "error",
                        "status": "failed",
                        "message": msg.get("message", "Pipeline failed"),
                    }),
                }
                break
            else:
                yield {
                    "event": "step",
                    "data": json.dumps({
                        "step": msg.get("step", "working"),
                        "status": "running",
                        "message": msg.get("message", "Working..."),
                    }),
                }

    return EventSourceResponse(event_generator())


# ── Synchronous Fallback Endpoint ───────────────────────────────────────────

@router.post("/run-sync", response_model=ResearchResponse)
async def run_research_sync(request: ResearchRequest):
    """Run the multi-agent research pipeline and return the complete result."""
    topic = request.topic.strip()

    try:
        loop = asyncio.get_event_loop()
        report = await loop.run_in_executor(
            None,
            run_research_pipeline,
            topic,
        )
        return ResearchResponse(topic=topic, report=report)

    except Exception as exc:
        logger.error("Pipeline failed: %s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Research pipeline failed: {str(exc)}")
