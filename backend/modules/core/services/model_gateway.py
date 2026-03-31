"""
Unified model gateway skeleton for provider-agnostic text generation.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field
from modules.core.services import prompt_registry


class GatewayRequest(BaseModel):
    task_type: str
    project_id: str
    trace_id: str
    messages: list[dict[str, str]] = Field(default_factory=list)
    provider: Literal["mock", "ollama", "groq"] = "mock"
    model: str = "default"
    prompt_id: str | None = None
    grounding: list[dict[str, Any]] = Field(default_factory=list)


class GatewayResponse(BaseModel):
    text: str
    provider: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    grounded: bool = False


async def generate(req: GatewayRequest) -> GatewayResponse:
    """
    Initial implementation uses a deterministic mock provider.
    This central contract allows modules to migrate incrementally.
    """
    template = prompt_registry.get_template(req.prompt_id) if req.prompt_id else None
    system_prompt = str(template.get("system_prompt", "")) if template else ""
    prompt = " ".join([m.get("content", "") for m in req.messages]).strip()
    grounded = len(req.grounding) > 0
    prefix = f"{system_prompt} " if system_prompt else ""
    text = f"[{req.task_type}] {prefix}{prompt[:320]}".strip()
    return GatewayResponse(
        text=text,
        provider=req.provider,
        model=req.model,
        tokens_in=max(1, len(prompt.split())),
        tokens_out=max(1, len(text.split())),
        grounded=grounded,
    )
