"""
Code Generator Service — Multi-phase LLM-driven code generation.

Pipeline:
  Phase 1 — Architecture blueprint (file list, class hierarchy, dependency DAG)
  Phase 2 — Sequential file generation in dependency order
  Phase 3 — Glue code (train.py, evaluate.py, config, requirements.txt, README)
"""

from __future__ import annotations

import json
import logging
from typing import Any

from modules.code_mapper.models.code_mapper_models import (
    CodeBlueprint,
    ExtractedMethodology,
    FileNode,
    GeneratedFile,
)
from modules.code_mapper.services import llm_client

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Phase 1 — Blueprint
# ---------------------------------------------------------------------------

_BLUEPRINT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "project_name": {"type": "string"},
        "description": {"type": "string"},
        "python_version": {"type": "string"},
        "files": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "description": {"type": "string"},
                    "dependencies": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["path", "description"],
            },
        },
        "dependency_order": {
            "type": "array",
            "items": {"type": "string"},
        },
        "packages": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["project_name", "files", "dependency_order", "packages"],
}


async def generate_blueprint(methodology: ExtractedMethodology) -> CodeBlueprint:
    """Phase 1: produce a project blueprint from extracted methodology."""

    system = (
        "You are an expert ML engineer. Given a methodology extracted from a research paper, "
        "design a clean Python project structure.\n\n"
        "Rules:\n"
        "- Use PyTorch as the default framework unless the paper specifies otherwise\n"
        "- Follow clean architecture: separate model, data, training, evaluation, utils\n"
        "- Include config.yaml for hyperparameters\n"
        "- List files in dependency_order (leaf modules first, composites last)\n"
        "- List pip packages needed in 'packages'\n"
        "- Keep it realistic and production-grade, not toy code\n"
        "Respond with JSON only."
    )

    user = (
        "Methodology:\n"
        f"Problem: {methodology.problem_statement}\n"
        f"Architecture: {methodology.model_architecture.description}\n"
        f"  Details: {json.dumps(methodology.model_architecture.details)}\n"
        f"Data Pipeline: {methodology.data_pipeline.description}\n"
        f"  Details: {json.dumps(methodology.data_pipeline.details)}\n"
        f"Loss: {', '.join(methodology.loss_functions)}\n"
        f"Training: {methodology.training_procedure.description}\n"
        f"  Details: {json.dumps(methodology.training_procedure.details)}\n"
        f"Metrics: {', '.join(methodology.evaluation_metrics)}\n"
        f"Hyperparameters: {json.dumps(methodology.hyperparameters)}\n"
        f"Equations: {'; '.join(methodology.key_equations[:10])}"
    )

    raw = await llm_client.chat_structured(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        _BLUEPRINT_SCHEMA,
        max_tokens=3000,
        temperature=0.2,
    )

    files = [
        FileNode(
            path=f.get("path", "unknown.py"),
            description=f.get("description", ""),
            dependencies=f.get("dependencies", []),
        )
        for f in raw.get("files", [])
    ]

    return CodeBlueprint(
        project_name=raw.get("project_name", "research_implementation"),
        description=raw.get("description", ""),
        python_version=raw.get("python_version", "3.10"),
        files=files,
        dependency_order=raw.get("dependency_order", [f.path for f in files]),
        packages=raw.get("packages", ["torch", "numpy"]),
    )


# ---------------------------------------------------------------------------
# Phase 2 — Sequential file generation
# ---------------------------------------------------------------------------

async def generate_file(
    file_node: FileNode,
    methodology: ExtractedMethodology,
    blueprint: CodeBlueprint,
    already_generated: dict[str, str],
) -> GeneratedFile:
    """Generate a single source file, given its blueprint node and any already-generated deps."""

    dep_context = ""
    for dep_path in file_node.dependencies:
        dep_code = already_generated.get(dep_path, "")
        if dep_code:
            dep_context += f"\n\n# --- {dep_path} ---\n{dep_code[:3000]}"

    system = (
        "You are an expert ML/DL engineer. Generate a complete, runnable Python file "
        "for the described component. The code must be:\n"
        "- Production-quality (not toy code)\n"
        "- Properly typed with type hints\n"
        "- Compatible with the project's other files\n"
        "- Realistic dimensions, hyperparameters, and logic\n\n"
        "Output ONLY the Python code, no markdown fences or explanation."
    )

    user = (
        f"File: {file_node.path}\n"
        f"Purpose: {file_node.description}\n"
        f"Project: {blueprint.project_name} — {blueprint.description}\n\n"
        f"Architecture: {methodology.model_architecture.description}\n"
        f"Architecture details: {json.dumps(methodology.model_architecture.details)}\n"
        f"Data pipeline: {methodology.data_pipeline.description}\n"
        f"Loss: {', '.join(methodology.loss_functions)}\n"
        f"Training: {methodology.training_procedure.description}\n"
        f"Hyperparameters: {json.dumps(methodology.hyperparameters)}\n"
        f"Packages: {', '.join(blueprint.packages)}\n"
    )

    if dep_context:
        user += f"\nAlready generated dependencies:{dep_context}"

    content = await llm_client.chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_tokens=6000,
        temperature=0.2,
    )

    content = _strip_markdown_fences(content)

    lang = "yaml" if file_node.path.endswith((".yaml", ".yml")) else "python"
    return GeneratedFile(path=file_node.path, content=content, language=lang)


# ---------------------------------------------------------------------------
# Phase 3 — Glue code generation
# ---------------------------------------------------------------------------

async def generate_glue_files(
    blueprint: CodeBlueprint,
    methodology: ExtractedMethodology,
    generated_files: dict[str, str],
) -> list[GeneratedFile]:
    """Generate README.md, requirements.txt, and any missing config files."""

    glue: list[GeneratedFile] = []

    pkg_lines = "\n".join(blueprint.packages)
    glue.append(GeneratedFile(
        path="requirements.txt",
        content=pkg_lines + "\n",
        language="text",
    ))

    readme = await _generate_readme(blueprint, methodology)
    glue.append(GeneratedFile(path="README.md", content=readme, language="markdown"))

    has_config = any("config" in f.path.lower() for f in blueprint.files)
    if not has_config:
        config = _build_default_config(methodology)
        glue.append(GeneratedFile(path="config.yaml", content=config, language="yaml"))

    gitignore = (
        "__pycache__/\n*.pyc\n*.pyo\n.env\n*.egg-info/\n"
        "dist/\nbuild/\n.venv/\nwandb/\nruns/\ncheckpoints/\n"
    )
    glue.append(GeneratedFile(path=".gitignore", content=gitignore, language="text"))

    return glue


async def generate_all_files(
    blueprint: CodeBlueprint,
    methodology: ExtractedMethodology,
) -> list[GeneratedFile]:
    """Run the full Phase 2 + Phase 3 pipeline."""

    generated: dict[str, str] = {}
    result_files: list[GeneratedFile] = []

    for file_path in blueprint.dependency_order:
        node = next((f for f in blueprint.files if f.path == file_path), None)
        if node is None:
            continue

        gf = await generate_file(node, methodology, blueprint, generated)
        generated[gf.path] = gf.content
        result_files.append(gf)

    remaining = [f for f in blueprint.files if f.path not in generated]
    for node in remaining:
        gf = await generate_file(node, methodology, blueprint, generated)
        generated[gf.path] = gf.content
        result_files.append(gf)

    glue = await generate_glue_files(blueprint, methodology, generated)
    result_files.extend(glue)

    return result_files


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_markdown_fences(text: str) -> str:
    lines = text.strip().split("\n")
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines)


async def _generate_readme(
    blueprint: CodeBlueprint, methodology: ExtractedMethodology
) -> str:
    system = (
        "You are a technical writer. Generate a concise README.md for a research "
        "code repository. Include: project description, setup instructions, "
        "usage examples, and file structure overview. Use markdown formatting."
    )
    user = (
        f"Project: {blueprint.project_name}\n"
        f"Description: {blueprint.description}\n"
        f"Problem: {methodology.problem_statement}\n"
        f"Architecture: {methodology.model_architecture.description}\n"
        f"Files: {', '.join(f.path for f in blueprint.files)}\n"
        f"Packages: {', '.join(blueprint.packages)}\n"
        f"Python version: {blueprint.python_version}"
    )
    return await llm_client.chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_tokens=2000,
        temperature=0.3,
    )


def _build_default_config(methodology: ExtractedMethodology) -> str:
    import yaml

    config: dict[str, Any] = {"model": {}, "training": {}, "data": {}}

    arch = methodology.model_architecture.details
    if arch:
        config["model"] = {k: v for k, v in arch.items() if v and v != "not specified"}

    train = methodology.training_procedure.details
    if train:
        config["training"] = {k: v for k, v in train.items() if v and v != "not specified"}

    data = methodology.data_pipeline.details
    if data:
        config["data"] = {k: v for k, v in data.items() if v and v != "not specified"}

    if methodology.hyperparameters:
        config["hyperparameters"] = methodology.hyperparameters

    try:
        return yaml.dump(config, default_flow_style=False, sort_keys=False)
    except ImportError:
        lines = []
        for section, vals in config.items():
            lines.append(f"{section}:")
            if isinstance(vals, dict):
                for k, v in vals.items():
                    lines.append(f"  {k}: {v}")
            lines.append("")
        return "\n".join(lines)
