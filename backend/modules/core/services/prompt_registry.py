"""
Prompt registry loader backed by JSON defaults and PostgreSQL persistence.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from modules.core.services import postgres_store

_REGISTRY_PATH = Path(__file__).resolve().parents[1] / "prompts" / "registry.json"


def _file_templates() -> list[dict[str, Any]]:
    if not _REGISTRY_PATH.exists():
        return []
    raw = json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
    return raw if isinstance(raw, list) else []


def ensure_seeded() -> None:
    if not postgres_store.database_enabled():
        return
    existing = postgres_store.list_prompt_templates()
    if existing:
        return
    for item in _file_templates():
        postgres_store.create_prompt_template(
            template_id=str(item.get("id")),
            task_type=str(item.get("task_type", "general")),
            title=str(item.get("title", "Untitled Prompt")),
            system_prompt=str(item.get("system_prompt", "")),
            metadata=item.get("metadata") if isinstance(item.get("metadata"), dict) else {},
        )


def list_templates(task_type: str | None = None) -> list[dict[str, Any]]:
    if postgres_store.database_enabled():
        ensure_seeded()
        return postgres_store.list_prompt_templates(task_type)
    data = _file_templates()
    if task_type:
        data = [item for item in data if item.get("task_type") == task_type]
    return data


def get_template(template_id: str) -> dict[str, Any] | None:
    templates = list_templates()
    return next((item for item in templates if item.get("id") == template_id), None)
