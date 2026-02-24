"""
Mermaid Service

Stores and returns Mermaid diagram definitions.
Rendering is done on the frontend using Mermaid.js.
"""

from modules.visualization.models.diagram_model import DiagramFormat


def validate_mermaid(definition: str) -> bool:
    """Basic validation that the definition looks like Mermaid syntax."""
    stripped = definition.strip()
    valid_prefixes = [
        "graph ",
        "graph\n",
        "flowchart ",
        "flowchart\n",
        "sequenceDiagram",
        "classDiagram",
        "stateDiagram",
        "erDiagram",
        "gantt",
        "pie",
        "gitGraph",
        "mindmap",
        "timeline",
    ]
    return any(stripped.startswith(prefix) for prefix in valid_prefixes)


def prepare_mermaid_response(definition: str) -> dict:
    """Validate and return a Mermaid definition for frontend rendering."""
    is_valid = validate_mermaid(definition)
    return {
        "diagram_definition": definition,
        "format": DiagramFormat.MERMAID,
        "valid": is_valid,
    }
