"""
Visualization Routes

POST /api/visualization/diagram/generate  — nodes+edges → definition
POST /api/visualization/diagram/render    — DOT → SVG
POST /api/visualization/chart/generate    — data → chart
POST /api/visualization/export            — SVG → PNG/PDF file
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from modules.visualization.models.diagram_model import (
    DiagramFormat,
    DiagramGenerateRequest,
    DiagramGenerateResponse,
    DiagramRenderRequest,
    DiagramRenderResponse,
    ExportRequest,
    ExportFormat,
)
from modules.visualization.models.chart_model import (
    ChartGenerateRequest,
    ChartGenerateResponse,
)
from modules.visualization.services import (
    diagram_generation_service,
    graphviz_render_service,
    mermaid_service,
    plotly_chart_service,
    export_service,
)

router = APIRouter()


@router.post("/diagram/generate", response_model=DiagramGenerateResponse)
async def generate_diagram(req: DiagramGenerateRequest) -> DiagramGenerateResponse:
    """Generate a diagram definition from structured nodes and edges."""
    try:
        return diagram_generation_service.generate(req)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Diagram generation failed: {str(exc)}")


@router.post("/diagram/render", response_model=DiagramRenderResponse)
async def render_diagram(req: DiagramRenderRequest) -> DiagramRenderResponse:
    """Render a Graphviz DOT definition to SVG."""
    if req.format == DiagramFormat.MERMAID:
        # Mermaid is rendered on the frontend — just validate and return
        result = mermaid_service.prepare_mermaid_response(req.definition)
        return DiagramRenderResponse(svg="", engine="mermaid")

    try:
        return graphviz_render_service.render(req)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Rendering failed: {str(exc)}")


@router.post("/chart/generate", response_model=ChartGenerateResponse)
async def generate_chart(req: ChartGenerateRequest) -> ChartGenerateResponse:
    """Generate a chart from structured data."""
    try:
        return plotly_chart_service.generate_chart(req)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Chart generation failed: {str(exc)}")


@router.post("/export")
async def export_diagram(req: ExportRequest):
    """Export SVG content to PNG, PDF, or SVG file."""
    try:
        file_bytes, content_type = export_service.export_svg_to_format(
            svg_content=req.svg_content,
            export_format=req.format,
            width=req.width,
            height=req.height,
        )

        filename = f"diagram.{req.format.value}"
        return Response(
            content=file_bytes,
            media_type=content_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(exc)}")
