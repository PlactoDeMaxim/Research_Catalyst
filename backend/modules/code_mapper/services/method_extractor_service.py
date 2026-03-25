"""
Methodology Extractor Service — LLM-driven structured extraction.

Takes a parsed research document and extracts:
  - Problem statement
  - Data pipeline description
  - Model architecture
  - Loss functions
  - Training procedure
  - Evaluation metrics
  - Hyperparameters
  - Key equations

Returns an ``ExtractedMethodology`` object used to drive code generation.
"""

from __future__ import annotations

import logging
from typing import Any

from modules.code_mapper.models.code_mapper_models import (
    ExtractedMethodology,
    MethodologyComponent,
    ParsedDocument,
)
from modules.code_mapper.services import llm_client

logger = logging.getLogger(__name__)

_EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "problem_statement": {"type": "string"},
        "data_pipeline": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "description": {"type": "string"},
                "details": {
                    "type": "object",
                    "properties": {
                        "dataset": {"type": "string"},
                        "preprocessing": {"type": "string"},
                        "augmentation": {"type": "string"},
                        "input_format": {"type": "string"},
                        "batch_size": {"type": "string"},
                    },
                },
            },
        },
        "model_architecture": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "description": {"type": "string"},
                "details": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"},
                        "layers": {"type": "string"},
                        "key_components": {"type": "string"},
                        "input_shape": {"type": "string"},
                        "output_shape": {"type": "string"},
                    },
                },
            },
        },
        "loss_functions": {"type": "array", "items": {"type": "string"}},
        "training_procedure": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "description": {"type": "string"},
                "details": {
                    "type": "object",
                    "properties": {
                        "optimizer": {"type": "string"},
                        "learning_rate": {"type": "string"},
                        "scheduler": {"type": "string"},
                        "epochs": {"type": "string"},
                        "hardware": {"type": "string"},
                    },
                },
            },
        },
        "evaluation_metrics": {"type": "array", "items": {"type": "string"}},
        "hyperparameters": {"type": "object"},
        "key_equations": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "problem_statement",
        "model_architecture",
        "loss_functions",
        "training_procedure",
        "evaluation_metrics",
    ],
}


def _build_extraction_prompt(doc: ParsedDocument) -> list[dict[str, str]]:
    section_text = ""
    for sec in doc.sections:
        section_text += f"\n\n## {sec.heading}\n{sec.content[:3000]}"
    section_text = section_text[:25_000]

    system = (
        "You are an expert ML/DL research analyst. Your job is to read a research paper "
        "and extract a precise, structured description of the methodology that can be "
        "used to re-implement the paper as runnable Python code.\n\n"
        "Focus on:\n"
        "1. The exact model architecture (layers, dimensions, activations)\n"
        "2. Data pipeline (dataset, preprocessing, augmentation)\n"
        "3. Loss functions used\n"
        "4. Training procedure (optimizer, lr, scheduler, epochs)\n"
        "5. Evaluation metrics\n"
        "6. Key hyperparameters\n"
        "7. Important equations\n\n"
        "Be specific and quantitative. If a detail is not mentioned, note 'not specified' "
        "rather than guessing.\n"
        "Respond ONLY with a JSON object."
    )

    user = (
        f"Paper Title: {doc.title}\n"
        f"Abstract: {doc.abstract[:2000]}\n"
        f"\nSections:{section_text}\n"
        f"\nFigure captions: {'; '.join(doc.figures[:10])}\n"
        f"Table captions: {'; '.join(doc.tables[:10])}"
    )

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


async def extract_methodology(doc: ParsedDocument) -> ExtractedMethodology:
    """Run the full LLM extraction pipeline and return structured methodology."""

    messages = _build_extraction_prompt(doc)
    raw = await llm_client.chat_structured(
        messages,
        _EXTRACTION_SCHEMA,
        max_tokens=4096,
        temperature=0.2,
    )

    return _parse_response(raw)


def _parse_response(data: dict[str, Any]) -> ExtractedMethodology:
    def _component(d: Any, fallback_name: str) -> MethodologyComponent:
        if isinstance(d, dict):
            return MethodologyComponent(
                name=d.get("name", fallback_name),
                description=d.get("description", ""),
                details=d.get("details", {}),
            )
        return MethodologyComponent(name=fallback_name)

    return ExtractedMethodology(
        problem_statement=data.get("problem_statement", ""),
        data_pipeline=_component(data.get("data_pipeline"), "data_pipeline"),
        model_architecture=_component(data.get("model_architecture"), "model_architecture"),
        loss_functions=data.get("loss_functions", []),
        training_procedure=_component(data.get("training_procedure"), "training_procedure"),
        evaluation_metrics=data.get("evaluation_metrics", []),
        hyperparameters=data.get("hyperparameters", {}),
        key_equations=data.get("key_equations", []),
    )
