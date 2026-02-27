"""
Project Store — In-memory project + milestone CRUD service.

Provides thread-safe storage for projects and their milestones.
Can be replaced with a database-backed store (e.g. Prisma/PostgreSQL) later.
"""

import uuid
from datetime import datetime
from typing import Optional

from modules.planner.models.planner_model import (
    Project,
    Milestone,
    Phase,
    ProjectCreateRequest,
    MilestoneCreateRequest,
    MilestoneUpdateRequest,
)
from modules.planner.services.rule_engine import generate_plan
from modules.planner.services.llm_engine import generate_plan_with_llm


# ── In-Memory Store ──
_projects: dict[str, Project] = {}


def list_projects() -> list[Project]:
    """Return all projects (without full milestone details for listing)."""
    return list(_projects.values())


def get_project(project_id: str) -> Optional[Project]:
    """Get a single project with all its data."""
    return _projects.get(project_id)


def create_project(req: ProjectCreateRequest) -> Project:
    """Create a new empty project."""
    project = Project(
        id=str(uuid.uuid4()),
        title=req.title,
        topic=req.topic,
        domain=req.domain,
        deadline=req.deadline,
        created_at=datetime.now().isoformat(),
        phases=[],
        milestones=[],
    )
    _projects[project.id] = project
    return project


def delete_project(project_id: str) -> bool:
    """Delete a project."""
    if project_id in _projects:
        del _projects[project_id]
        return True
    return False


def generate_project_plan(project_id: str, topic: str = "", domain: str = "general", deadline: str = "") -> Optional[Project]:
    """Generate a plan for a project using LLM (with rule engine fallback)."""
    project = _projects.get(project_id)
    if not project:
        return None

    # Use project fields as defaults if not overridden
    t = topic or project.topic
    d = domain or project.domain
    dl = deadline or project.deadline

    # Update project with the provided values
    project.topic = t
    project.domain = d
    project.deadline = dl

    # Try LLM first
    # print(f"Attempting LLM plan generation for project {project_id}...")
    result = generate_plan_with_llm(t, d, dl)
    
    if result is not None:
        # print(f"✓ LLM plan generation successful")
        phases, milestones = result
    else:
        # Fallback to rule engine
        # print(f"⚠ LLM failed, falling back to rule engine")
        phases, milestones = generate_plan(t, d, dl)
    
    project.phases = phases
    project.milestones = milestones

    _projects[project.id] = project
    return project


def add_milestone(project_id: str, req: MilestoneCreateRequest) -> Optional[Milestone]:
    """Add a milestone to a project."""
    project = _projects.get(project_id)
    if not project:
        return None

    milestone = Milestone(
        id=str(uuid.uuid4()),
        title=req.title,
        description=req.description,
        due_date=req.due_date,
        completed=False,
        phase=req.phase,
        order=len(project.milestones),
    )

    project.milestones.append(milestone)

    # Also add to the appropriate phase
    for phase in project.phases:
        if phase.title == req.phase:
            phase.milestones.append(milestone)
            break

    _projects[project.id] = project
    return milestone


def update_milestone(project_id: str, milestone_id: str, req: MilestoneUpdateRequest) -> Optional[Milestone]:
    """Update a milestone in a project."""
    project = _projects.get(project_id)
    if not project:
        return None

    for i, m in enumerate(project.milestones):
        if m.id == milestone_id:
            if req.title is not None:
                m.title = req.title
            if req.description is not None:
                m.description = req.description
            if req.due_date is not None:
                m.due_date = req.due_date
            if req.completed is not None:
                m.completed = req.completed
            if req.phase is not None:
                m.phase = req.phase

            project.milestones[i] = m

            # Also update in the phase
            for phase in project.phases:
                for j, pm in enumerate(phase.milestones):
                    if pm.id == milestone_id:
                        phase.milestones[j] = m
                        break

            _projects[project.id] = project
            return m

    return None


def delete_milestone(project_id: str, milestone_id: str) -> bool:
    """Delete a milestone from a project."""
    project = _projects.get(project_id)
    if not project:
        return False

    original_len = len(project.milestones)
    project.milestones = [m for m in project.milestones if m.id != milestone_id]

    # Also remove from phases
    for phase in project.phases:
        phase.milestones = [m for m in phase.milestones if m.id != milestone_id]

    _projects[project.id] = project
    return len(project.milestones) < original_len