"""
Research Catalyst — FastAPI Backend Service

Hosts:
  - Paper Discovery Service  (/api/papers)
  - Visualization Studio     (/api/visualization)

Run with:  uvicorn main:app --reload --port 8000
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from modules.paper_search.routes.search_routes import router as search_router
from modules.visualization.routes.visualization_routes import router as viz_router
from modules.planner.routes.planner_routes import router as planner_router
from modules.summary.routes.summary_routes import router as summary_router
from modules.paper_editor.routes.paper_editor_routes import router as paper_editor_router
from modules.plagiarism_check.routes.plagiarism_routes import router as plagiarism_router
from modules.citation_manager.routes.citation_manager_routes import router as citation_manager_router

app = FastAPI(
    title="Research Catalyst Backend",
    description="Backend microservice for the AI Research Paper Assistance Platform",
    version="1.0.0",
)

# ── CORS — allow the Next.js frontend (comma-separated in CORS_ORIGINS) ──
_cors_origins = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount routes ──
app.include_router(search_router, prefix="/api/papers")
app.include_router(viz_router, prefix="/api/visualization")
app.include_router(planner_router, prefix="/api/planner")
app.include_router(summary_router, prefix="/api/summary")
app.include_router(paper_editor_router, prefix="/api/paper-editor")
app.include_router(plagiarism_router, prefix="/api/plagiarism-check")
app.include_router(citation_manager_router, prefix="/api/citation-manager")


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "research-catalyst-backend"}
