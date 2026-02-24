"""
Chart models — request/response schemas for chart operations.
"""

from pydantic import BaseModel
from typing import Optional
from enum import Enum


class ChartType(str, Enum):
    LINE = "line"
    BAR = "bar"
    SCATTER = "scatter"


class DataSeries(BaseModel):
    x: list[float | int | str]
    y: list[float | int]
    label: str = ""


class ChartGenerateRequest(BaseModel):
    """Generate a chart from structured data."""
    chart_type: ChartType = ChartType.LINE
    data: list[DataSeries]
    title: str = ""
    x_label: str = ""
    y_label: str = ""


class ChartGenerateResponse(BaseModel):
    chart_config: dict  # Plotly JSON config for frontend rendering
    svg: str            # Pre-rendered SVG
