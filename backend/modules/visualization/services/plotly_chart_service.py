"""
Plotly Chart Service

Generates charts from structured data using Plotly.
Returns both Plotly JSON config (for frontend) and pre-rendered SVG.
"""

import json
import plotly.graph_objects as go
from modules.visualization.models.chart_model import (
    ChartType,
    ChartGenerateRequest,
    ChartGenerateResponse,
)

# Branded color palette
COLORS = [
    "#2c6a73",  # primary teal
    "#e8856e",  # warm coral
    "#429fad",  # light blue
    "#c49a2a",  # amber
    "#1b9179",  # icy aqua
    "#b31b1b",  # deep red
]


def generate_chart(req: ChartGenerateRequest) -> ChartGenerateResponse:
    """Generate a chart from structured data."""
    fig = go.Figure()

    for i, series in enumerate(req.data):
        color = COLORS[i % len(COLORS)]

        if req.chart_type == ChartType.LINE:
            fig.add_trace(
                go.Scatter(
                    x=series.x,
                    y=series.y,
                    mode="lines+markers",
                    name=series.label or f"Series {i + 1}",
                    line=dict(color=color, width=2),
                    marker=dict(size=6),
                )
            )
        elif req.chart_type == ChartType.BAR:
            fig.add_trace(
                go.Bar(
                    x=series.x,
                    y=series.y,
                    name=series.label or f"Series {i + 1}",
                    marker_color=color,
                )
            )
        elif req.chart_type == ChartType.SCATTER:
            fig.add_trace(
                go.Scatter(
                    x=series.x,
                    y=series.y,
                    mode="markers",
                    name=series.label or f"Series {i + 1}",
                    marker=dict(color=color, size=8),
                )
            )

    # Layout
    fig.update_layout(
        title=dict(text=req.title, font=dict(family="Inter", size=16)),
        xaxis_title=req.x_label,
        yaxis_title=req.y_label,
        font=dict(family="Inter", size=12),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=60, r=30, t=50, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    fig.update_xaxes(showgrid=True, gridcolor="#e5e7eb")
    fig.update_yaxes(showgrid=True, gridcolor="#e5e7eb")

    # Generate SVG
    svg_str = fig.to_image(format="svg", width=800, height=500).decode("utf-8")

    # Generate Plotly JSON config for frontend rendering
    chart_config = json.loads(fig.to_json())

    return ChartGenerateResponse(
        chart_config=chart_config,
        svg=svg_str,
    )
