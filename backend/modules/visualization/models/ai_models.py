"""
AI Diagram Models — request/response schemas for AI-powered diagram generation.
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

from modules.visualization.models.diagram_model import DiagramFormat, DiagramType


class TextToDiagramRequest(BaseModel):
    """Generate a diagram from research paper text or methodology description."""
    text: str = Field(..., description="Research text, methodology, or any natural language description")
    diagram_type: DiagramType = DiagramType.FLOWCHART
    format: DiagramFormat = DiagramFormat.MERMAID
    title: str = ""


class CodeToDiagramRequest(BaseModel):
    """Generate a diagram from source code."""
    code: str = Field(..., description="Source code to analyze")
    language: str = Field(default="python", description="Programming language (python, javascript, java, etc.)")
    diagram_type: DiagramType = DiagramType.ARCHITECTURE
    format: DiagramFormat = DiagramFormat.MERMAID
    title: str = ""


class AIDiagramResponse(BaseModel):
    """Response from AI-powered diagram generation."""
    nodes: list[dict] = Field(default_factory=list, description="List of nodes with id, label, and optional type")
    edges: list[dict] = Field(default_factory=list, description="List of edges with source, target, and optional label")
    title: str = ""
    diagram_definition: str = ""
    format: DiagramFormat = DiagramFormat.MERMAID
    diagram_type: DiagramType = DiagramType.FLOWCHART
    ai_generated: bool = True
