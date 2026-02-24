"""
Graphviz Render Service

Accepts DOT definitions and renders them to SVG using Graphviz.
"""

import os
import graphviz as gv
from modules.visualization.models.diagram_model import (
    DiagramRenderRequest,
    DiagramRenderResponse,
)

# Ensure Graphviz binaries are discoverable on Windows
_GV_PATHS = [
    r"C:\Program Files\Graphviz\bin",
    r"C:\Program Files (x86)\Graphviz\bin",
]
for p in _GV_PATHS:
    if os.path.isdir(p) and p not in os.environ.get("PATH", ""):
        os.environ["PATH"] = p + os.pathsep + os.environ.get("PATH", "")
        break


def render(req: DiagramRenderRequest) -> DiagramRenderResponse:
    """Render a DOT definition to SVG."""
    src = gv.Source(
        req.definition,
        engine=req.engine,
        format="svg",
    )

    # .pipe() returns the rendered output as bytes
    svg_bytes = src.pipe(format="svg")
    svg_str = svg_bytes.decode("utf-8")

    return DiagramRenderResponse(
        svg=svg_str,
        engine=req.engine,
    )
