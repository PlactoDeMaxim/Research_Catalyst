"""
Diagram Generation Service

Converts structured input (nodes + edges) into Graphviz DOT or Mermaid definitions.
"""

from modules.visualization.models.diagram_model import (
    DiagramFormat,
    DiagramType,
    DiagramGenerateRequest,
    DiagramGenerateResponse,
)


def _generate_dot(req: DiagramGenerateRequest) -> str:
    """Generate a Graphviz DOT definition from nodes and edges."""
    graph_type = "digraph" if req.type != DiagramType.ARCHITECTURE else "graph"
    connector = " -> " if graph_type == "digraph" else " -- "

    lines = [f'{graph_type} G {{']
    lines.append('  rankdir=TB;')
    lines.append('  node [shape=box, style="rounded,filled", fillcolor="#e8f4f6", fontname="Inter", fontsize=11, color="#2c6a73"];')
    lines.append('  edge [color="#5e6472", fontname="Inter", fontsize=9];')

    if req.title:
        lines.append(f'  labelloc="t";')
        lines.append(f'  label="{req.title}";')
        lines.append(f'  fontname="Inter";')
        lines.append(f'  fontsize=14;')

    # Add nodes
    for node in req.nodes:
        safe_id = node.replace(" ", "_").replace("-", "_")
        lines.append(f'  {safe_id} [label="{node}"];')

    # Add edges
    for edge in req.edges:
        if len(edge) >= 2:
            src = edge[0].replace(" ", "_").replace("-", "_")
            tgt = edge[1].replace(" ", "_").replace("-", "_")
            label = edge[2] if len(edge) > 2 else ""
            label_attr = f' [label="{label}"]' if label else ""
            lines.append(f'  {src}{connector}{tgt}{label_attr};')

    lines.append('}')
    return "\n".join(lines)


def _generate_mermaid(req: DiagramGenerateRequest) -> str:
    """Generate a Mermaid definition from nodes and edges."""
    if req.type == DiagramType.SEQUENCE:
        lines = ["sequenceDiagram"]
        for edge in req.edges:
            if len(edge) >= 2:
                label = edge[2] if len(edge) > 2 else ""
                lines.append(f"  {edge[0]}->>{edge[1]}: {label}")
        return "\n".join(lines)

    # Default: flowchart
    lines = ["graph TD"]
    node_map: dict[str, str] = {}
    for i, node in enumerate(req.nodes):
        nid = chr(65 + i) if i < 26 else f"N{i}"
        node_map[node] = nid
        lines.append(f'  {nid}["{node}"]')

    for edge in req.edges:
        if len(edge) >= 2:
            src = node_map.get(edge[0], edge[0])
            tgt = node_map.get(edge[1], edge[1])
            label = edge[2] if len(edge) > 2 else ""
            if label:
                lines.append(f"  {src} -->|{label}| {tgt}")
            else:
                lines.append(f"  {src} --> {tgt}")

    return "\n".join(lines)


def generate(req: DiagramGenerateRequest) -> DiagramGenerateResponse:
    """Generate a diagram definition from structured input."""
    if req.format == DiagramFormat.MERMAID:
        definition = _generate_mermaid(req)
    else:
        definition = _generate_dot(req)

    return DiagramGenerateResponse(
        diagram_definition=definition,
        format=req.format,
        diagram_type=req.type,
    )
