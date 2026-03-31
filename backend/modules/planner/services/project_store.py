"""
Project Store — In-memory project + milestone CRUD service.

Provides thread-safe storage for projects and their milestones.
Can be replaced with a database-backed store (e.g. Prisma/PostgreSQL) later.
"""

import uuid
from datetime import datetime
from typing import Optional

from modules.core.services import postgres_store
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


def _project_from_db(project_row: dict, milestone_rows: list[dict]) -> Project:
    metadata = project_row.get("metadata") or {}
    raw_phases = metadata.get("phases") or []
    phases = [Phase.model_validate(item) for item in raw_phases]
    milestones = [
        Milestone(
            id=row["id"],
            title=row["title"],
            description=row.get("description", ""),
            due_date=row.get("due_date", ""),
            completed=bool(row.get("completed", False)),
            phase=row.get("phase", ""),
            order=int(row.get("ordering", 0)),
        )
        for row in milestone_rows
    ]
    if not phases and milestones:
        phase_names = [m.phase for m in milestones if m.phase]
        unique_phase_names = list(dict.fromkeys(phase_names))
        phases = [
            Phase(
                title=name,
                order=index,
                milestones=[m for m in milestones if m.phase == name],
            )
            for index, name in enumerate(unique_phase_names)
        ]
    else:
        for phase in phases:
            phase.milestones = [m for m in milestones if m.phase == phase.title]
    return Project(
        id=project_row["id"],
        title=project_row["title"],
        topic=project_row.get("topic", ""),
        domain=project_row.get("domain", "general"),
        deadline=project_row.get("deadline", ""),
        created_at=project_row.get("created_at", ""),
        phases=phases,
        milestones=milestones,
    )


def list_projects() -> list[Project]:
    """Return all projects (without full milestone details for listing)."""
    if postgres_store.database_enabled():
        projects = []
        for row in postgres_store.list_workspace_projects(kind="planner"):
            milestones = postgres_store.list_workspace_milestones(row["id"])
            projects.append(_project_from_db(row, milestones))
        return projects
    return list(_projects.values())


def get_project(project_id: str) -> Optional[Project]:
    """Get a single project with all its data."""
    if postgres_store.database_enabled():
        row = postgres_store.get_workspace_project(project_id)
        if not row or row.get("kind") != "planner":
            return None
        milestones = postgres_store.list_workspace_milestones(project_id)
        return _project_from_db(row, milestones)
    return _projects.get(project_id)


def create_project(req: ProjectCreateRequest) -> Project:
    """Create a new empty project."""
    if postgres_store.database_enabled():
        row = postgres_store.create_workspace_project(
            title=req.title,
            description="",
            kind="planner",
            topic=req.topic,
            domain=req.domain,
            deadline=req.deadline,
            metadata={"phases": []},
        )
        return _project_from_db(row, [])
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
    if postgres_store.database_enabled():
        return postgres_store.delete_workspace_project(project_id)
    if project_id in _projects:
        del _projects[project_id]
        return True
    return False


def generate_project_plan(project_id: str, topic: str = "", domain: str = "general", deadline: str = "") -> Optional[Project]:
    """Generate a plan for a project using LLM (with rule engine fallback)."""
    if postgres_store.database_enabled():
        existing = get_project(project_id)
        if not existing:
            return None

        t = topic or existing.topic
        d = domain or existing.domain
        dl = deadline or existing.deadline

        result = generate_plan_with_llm(t, d, dl)
        if result is not None:
            phases, milestones = result
        else:
            phases, milestones = generate_plan(t, d, dl)

        postgres_store.update_workspace_project(
            project_id,
            topic=t,
            domain=d,
            deadline=dl,
            metadata={"phases": [phase.model_dump() for phase in phases]},
        )
        postgres_store.replace_workspace_milestones(
            project_id,
            [milestone.model_dump() for milestone in milestones],
        )
        return get_project(project_id)

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
    if postgres_store.database_enabled():
        project = get_project(project_id)
        if not project:
            return None
        row = postgres_store.create_workspace_milestone(
            project_id=project_id,
            title=req.title,
            description=req.description,
            due_date=req.due_date,
            phase=req.phase,
            order=len(project.milestones),
        )
        return Milestone(
            id=row["id"],
            title=row["title"],
            description=row.get("description", ""),
            due_date=row.get("due_date", ""),
            completed=bool(row.get("completed", False)),
            phase=row.get("phase", ""),
            order=int(row.get("ordering", 0)),
        )
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
    if postgres_store.database_enabled():
        project = get_project(project_id)
        if not project:
            return None
        row = postgres_store.update_workspace_milestone(
            milestone_id,
            title=req.title,
            description=req.description,
            due_date=req.due_date,
            completed=req.completed,
            phase=req.phase,
        )
        if not row:
            return None
        return Milestone(
            id=row["id"],
            title=row["title"],
            description=row.get("description", ""),
            due_date=row.get("due_date", ""),
            completed=bool(row.get("completed", False)),
            phase=row.get("phase", ""),
            order=int(row.get("ordering", 0)),
        )
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
    if postgres_store.database_enabled():
        project = get_project(project_id)
        if not project:
            return False
        return postgres_store.delete_workspace_milestone(milestone_id)
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