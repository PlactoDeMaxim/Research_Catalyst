"""
Planner Models — request/response schemas for projects, phases, and milestones.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class Milestone(BaseModel):
    id: str = ""
    title: str
    description: str = ""
    due_date: str = ""        # ISO date string
    completed: bool = False
    phase: str = ""
    order: int = 0


class Phase(BaseModel):
    title: str
    description: str = ""
    order: int = 0
    milestones: list[Milestone] = Field(default_factory=list)


class Project(BaseModel):
    id: str = ""
    title: str
    topic: str = ""
    domain: str = "general"   # e.g. "machine_learning", "biology", "general"
    deadline: str = ""        # ISO date string
    created_at: str = ""
    phases: list[Phase] = Field(default_factory=list)
    milestones: list[Milestone] = Field(default_factory=list)


class ProjectCreateRequest(BaseModel):
    title: str
    topic: str = ""
    domain: str = "general"
    deadline: str = ""        # ISO date string, e.g. "2026-06-01"


class PlanGenerateRequest(BaseModel):
    topic: str = ""
    domain: str = "general"
    deadline: str = ""        # ISO date string


class MilestoneCreateRequest(BaseModel):
    title: str
    description: str = ""
    due_date: str = ""
    phase: str = ""


class MilestoneUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[str] = None
    completed: Optional[bool] = None
    phase: Optional[str] = None
