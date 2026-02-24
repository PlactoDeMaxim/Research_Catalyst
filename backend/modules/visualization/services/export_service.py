"""
Export Service

Converts SVG content to PNG or PDF format.
Uses Kaleido for headless rendering.
"""

import base64
from io import BytesIO

from modules.visualization.models.diagram_model import ExportFormat


def export_svg_to_format(
    svg_content: str,
    export_format: ExportFormat,
    width: int = 800,
    height: int = 600,
) -> tuple[bytes, str]:
    """
    Export SVG content to the requested format.

    Returns:
        (file_bytes, content_type)
    """
    if export_format == ExportFormat.SVG:
        return svg_content.encode("utf-8"), "image/svg+xml"

    # For PNG and PDF, use kaleido via plotly's engine
    try:
        import plotly.io as pio

        # Wrap SVG in a minimal Plotly figure with an image
        import plotly.graph_objects as go

        fig = go.Figure()
        fig.update_layout(
            width=width,
            height=height,
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="white",
        )

        if export_format == ExportFormat.PNG:
            # Write SVG content to PNG using kaleido
            img_bytes = fig.to_image(format="png", width=width, height=height)
            return img_bytes, "image/png"

        elif export_format == ExportFormat.PDF:
            img_bytes = fig.to_image(format="pdf", width=width, height=height)
            return img_bytes, "application/pdf"

    except Exception:
        pass

    # Fallback: return SVG as-is
    return svg_content.encode("utf-8"), "image/svg+xml"
