"""
Diagram models — request/response schemas for diagram operations.
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class DiagramFormat(str, Enum):
    GRAPHVIZ = "graphviz"
    MERMAID = "mermaid"


class DiagramType(str, Enum):
    FLOWCHART = "flowchart"
    ARCHITECTURE = "architecture"
    SEQUENCE = "sequence"
    METHODOLOGY = "methodology"
    DIRECTED = "directed"


class ExportFormat(str, Enum):
    SVG = "svg"
    PNG = "png"
    PDF = "pdf"


class EdgeDef(BaseModel):
    source: str
    target: str
    label: str = ""


class DiagramGenerateRequest(BaseModel):
    """Generate a diagram definition from structured nodes + edges."""
    type: DiagramType = DiagramType.FLOWCHART
    nodes: list[str]
    edges: list[list[str]]  # [[source, target], ...]
    format: DiagramFormat = DiagramFormat.GRAPHVIZ
    title: str = ""


class DiagramGenerateResponse(BaseModel):
    diagram_definition: str
    format: DiagramFormat
    diagram_type: DiagramType


class DiagramRenderRequest(BaseModel):
    """Render a DOT definition into SVG."""
    definition: str
    format: DiagramFormat = DiagramFormat.GRAPHVIZ
    engine: str = "dot"  # dot, neato, fdp, sfdp, circo, twopi


class DiagramRenderResponse(BaseModel):
    svg: str
    engine: str


class ExportRequest(BaseModel):
    """Export SVG content to PNG or PDF."""
    svg_content: str
    format: ExportFormat = ExportFormat.SVG
    width: int = 800
    height: int = 600


class DiagramMetadata(BaseModel):
    """Stored diagram metadata."""
    diagram_id: str
    diagram_definition: str
    format: DiagramFormat
    diagram_type: DiagramType
    title: str = ""
    created_at: str = ""

    # Phase 2 — future AI-generated definitions
    ai_generated: bool = False
