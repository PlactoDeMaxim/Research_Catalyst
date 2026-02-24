"""
Planner Routes

Projects CRUD + Milestones CRUD + Plan Generation.
"""

from fastapi import APIRouter, HTTPException

from modules.planner.models.planner_model import (
    ProjectCreateRequest,
    PlanGenerateRequest,
    MilestoneCreateRequest,
    MilestoneUpdateRequest,
)
from modules.planner.services import project_store


router = APIRouter()


# ── Projects ──

@router.get("/projects")
async def list_projects():
    """List all projects."""
    projects = project_store.list_projects()
    return {"projects": [p.model_dump() for p in projects]}


@router.post("/projects")
async def create_project(req: ProjectCreateRequest):
    """Create a new project."""
    project = project_store.create_project(req)
    return project.model_dump()


@router.get("/projects/{project_id}")
async def get_project(project_id: str):
    """Get a project with all phases and milestones."""
    project = project_store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project.model_dump()


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete a project."""
    if not project_store.delete_project(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return {"deleted": True}


# ── Plan Generation ──

@router.post("/projects/{project_id}/generate")
async def generate_plan(project_id: str, req: PlanGenerateRequest):
    """Generate a research plan for a project using the rule engine."""
    project = project_store.generate_project_plan(
        project_id,
        topic=req.topic,
        domain=req.domain,
        deadline=req.deadline,
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project.model_dump()


# ── Milestones ──

@router.post("/projects/{project_id}/milestones")
async def add_milestone(project_id: str, req: MilestoneCreateRequest):
    """Add a milestone to a project."""
    milestone = project_store.add_milestone(project_id, req)
    if not milestone:
        raise HTTPException(status_code=404, detail="Project not found")
    return milestone.model_dump()


@router.put("/projects/{project_id}/milestones/{milestone_id}")
async def update_milestone(project_id: str, milestone_id: str, req: MilestoneUpdateRequest):
    """Update a milestone."""
    milestone = project_store.update_milestone(project_id, milestone_id, req)
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
    return milestone.model_dump()


@router.delete("/projects/{project_id}/milestones/{milestone_id}")
async def delete_milestone(project_id: str, milestone_id: str):
    """Delete a milestone."""
    if not project_store.delete_milestone(project_id, milestone_id):
        raise HTTPException(status_code=404, detail="Milestone not found")
    return {"deleted": True}
