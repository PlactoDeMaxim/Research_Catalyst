"""
Pydantic models for the Code Mapper module.

Covers both features:
  Feature 1 — Paper-to-Code (AI Research Compiler)
  Feature 2 — Repo-to-Paper (GitHub → Research Paper Generator)
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared / Job infrastructure
# ---------------------------------------------------------------------------

class JobPhase(str, Enum):
    QUEUED = "queued"
    PARSING = "parsing"
    EXTRACTING = "extracting"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    VALIDATING = "validating"
    CITING = "citing"
    REFINING = "refining"
    PACKAGING = "packaging"
    EXPORTING = "exporting"
    COMPLETED = "completed"
    FAILED = "failed"


class JobStatus(BaseModel):
    job_id: str
    phase: JobPhase = JobPhase.QUEUED
    progress: float = Field(0.0, ge=0.0, le=100.0)
    message: str = ""
    artifact_path: Optional[str] = None
    error: Optional[str] = None
    result: Optional[dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Feature 1 — Paper-to-Code models
# ---------------------------------------------------------------------------

class PaperUploadResponse(BaseModel):
    job_id: str
    message: str = "Paper upload received. Processing started."


class ParsedSection(BaseModel):
    heading: str
    level: int = 1
    content: str = ""


class ParsedDocument(BaseModel):
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    abstract: str = ""
    sections: list[ParsedSection] = Field(default_factory=list)
    figures: list[str] = Field(default_factory=list)
    tables: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    raw_text: str = ""


class MethodologyComponent(BaseModel):
    name: str
    description: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


class ExtractedMethodology(BaseModel):
    problem_statement: str = ""
    data_pipeline: MethodologyComponent = Field(
        default_factory=lambda: MethodologyComponent(name="data_pipeline")
    )
    model_architecture: MethodologyComponent = Field(
        default_factory=lambda: MethodologyComponent(name="model_architecture")
    )
    loss_functions: list[str] = Field(default_factory=list)
    training_procedure: MethodologyComponent = Field(
        default_factory=lambda: MethodologyComponent(name="training_procedure")
    )
    evaluation_metrics: list[str] = Field(default_factory=list)
    hyperparameters: dict[str, Any] = Field(default_factory=dict)
    key_equations: list[str] = Field(default_factory=list)


class FileNode(BaseModel):
    path: str
    description: str = ""
    dependencies: list[str] = Field(default_factory=list)


class CodeBlueprint(BaseModel):
    project_name: str = "research_implementation"
    description: str = ""
    python_version: str = "3.10"
    files: list[FileNode] = Field(default_factory=list)
    dependency_order: list[str] = Field(default_factory=list)
    packages: list[str] = Field(default_factory=list)


class GeneratedFile(BaseModel):
    path: str
    content: str
    language: str = "python"


class ValidationResult(BaseModel):
    file_path: str
    passed: bool = False
    ast_valid: bool = False
    exec_valid: bool = False
    errors: list[str] = Field(default_factory=list)
    fix_attempts: int = 0


class PaperToCodeResult(BaseModel):
    methodology: ExtractedMethodology
    blueprint: CodeBlueprint
    files: list[GeneratedFile] = Field(default_factory=list)
    validation: list[ValidationResult] = Field(default_factory=list)
    zip_path: Optional[str] = None


# ---------------------------------------------------------------------------
# Feature 2 — Repo-to-Paper models
# ---------------------------------------------------------------------------

class RepoAnalyzeRequest(BaseModel):
    github_url: str
    include_experiments: bool = True
    paper_style: Literal["generic", "neurips", "icml", "arxiv"] = "generic"
    output_formats: list[Literal["latex", "word"]] = Field(
        default_factory=lambda: ["latex", "word"]
    )


class RepoAnalyzeResponse(BaseModel):
    job_id: str
    message: str = "Repository analysis started."


class RepoFileInfo(BaseModel):
    path: str
    language: str = ""
    size_bytes: int = 0
    summary: str = ""


class RepoStructure(BaseModel):
    name: str = ""
    description: str = ""
    languages: list[str] = Field(default_factory=list)
    total_files: int = 0
    file_tree: list[str] = Field(default_factory=list)
    key_files: list[RepoFileInfo] = Field(default_factory=list)
    readme_content: str = ""
    classes: list[dict[str, Any]] = Field(default_factory=list)
    functions: list[dict[str, Any]] = Field(default_factory=list)
    config_files: list[str] = Field(default_factory=list)
    training_scripts: list[str] = Field(default_factory=list)


class PaperSectionDraft(BaseModel):
    section_id: str
    title: str
    content: str = ""
    citations: list[str] = Field(default_factory=list)
    word_count: int = 0


class CitationEntry(BaseModel):
    cite_key: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int = 0
    venue: str = ""
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    url: str = ""
    bibtex: str = ""
    verified: bool = False
    verification_layers: list[str] = Field(default_factory=list)
    relevance_score: float = 0.0


class RepoToPaperResult(BaseModel):
    repo_structure: RepoStructure
    sections: list[PaperSectionDraft] = Field(default_factory=list)
    citations: list[CitationEntry] = Field(default_factory=list)
    bibtex_content: str = ""
    latex_path: Optional[str] = None
    word_path: Optional[str] = None


# ---------------------------------------------------------------------------
# Download endpoint helpers
# ---------------------------------------------------------------------------

class DownloadRequest(BaseModel):
    format: Literal["zip", "latex", "word"] = "zip"
