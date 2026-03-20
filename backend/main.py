"""
Research Catalyst — FastAPI Backend Service

Hosts:
  - Paper Discovery Service  (/api/papers)
  - Visualization Studio     (/api/visualization)

Run with:  uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from modules.paper_search.routes.search_routes import router as search_router
from modules.visualization.routes.visualization_routes import router as viz_router
from modules.planner.routes.planner_routes import router as planner_router
from modules.summary.routes.summary_routes import router as summary_router

app = FastAPI(
    title="Research Catalyst Backend",
    description="Backend microservice for the AI Research Paper Assistance Platform",
    version="1.0.0",
)

# ── CORS — allow the Next.js frontend ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount routes ──
app.include_router(search_router, prefix="/api/papers")
app.include_router(viz_router, prefix="/api/visualization")
app.include_router(planner_router, prefix="/api/planner")
app.include_router(summary_router, prefix="/api/summary")


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "research-catalyst-backend"}
