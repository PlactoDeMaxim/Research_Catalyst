from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


class PaperSection(BaseModel):
    id: str
    title: str
    content: str = ""


class GlobalContext(BaseModel):
    problem: str = ""
    contributions: list[str] = Field(default_factory=list)
    method_summary: str = ""


class StructuredPaper(BaseModel):
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    sections: list[PaperSection] = Field(default_factory=list)
    global_context: GlobalContext = Field(default_factory=GlobalContext)


class GenerateSectionRequest(BaseModel):
    paper: StructuredPaper
    section_id: str


class RefineSectionRequest(BaseModel):
    paper: StructuredPaper
    section_id: str
    draft: str


class GeneratedSectionResponse(BaseModel):
    section_id: str
    content: str
    critic_notes: list[str] = Field(default_factory=list)


class TemplateConstraints(BaseModel):
    strict_mode: bool = False
    required_sections: list[str] = Field(default_factory=list)
    allowed_extra_sections: bool = True
    section_order_fixed: bool = False


class TemplateSectionNode(BaseModel):
    id: str
    title: str
    level: int = 1
    latex_command: Literal["section", "subsection", "subsubsection", "abstract", "title", "author", "keywords", "impact"] = "section"
    editable: bool = True
    protected: bool = False
    order: int = 0


class StructureUpdateRequest(BaseModel):
    sections: list[PaperSection]
    constraints: TemplateConstraints


class StructureUpdateResponse(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    normalized_sections: list[PaperSection] = Field(default_factory=list)


class UploadTemplateResponse(BaseModel):
    template_id: str
    main_tex: str
    constraints: TemplateConstraints
    files: list[str]
    template_sections: list[TemplateSectionNode] = Field(default_factory=list)


class InjectRequest(BaseModel):
    template_id: str
    paper: StructuredPaper
    section_aliases: dict[str, list[str]] = Field(default_factory=dict)
    section_targets: dict[str, str] = Field(default_factory=dict)


class InjectResponse(BaseModel):
    template_id: str
    tex_path: str
    preview_snippet: str
    injected_source: str
    main_tex_path: str
    matched_sections: list[str] = Field(default_factory=list)
    skipped_sections: list[str] = Field(default_factory=list)
    appended_sections: list[str] = Field(default_factory=list)
    matched_details: list[str] = Field(default_factory=list)
    skipped_details: list[str] = Field(default_factory=list)


class CompileRequest(BaseModel):
    template_id: str
    max_retries: int = 2


class V2ProjectFile(BaseModel):
    path: str
    content: str = ""
    binary_base64: Optional[str] = None


class V2CompileSourceRequest(BaseModel):
    project_name: str = "Untitled Project"
    main_file_path: str = "main.tex"
    files: list[V2ProjectFile] = Field(default_factory=list)
    max_retries: int = 1


class CompileJobResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "succeeded", "failed"]
    message: str = ""


class CompilePreflightResponse(BaseModel):
    template_id: str
    mode: str
    docker_ready: bool
    image_ready: bool
    warnings: list[str] = Field(default_factory=list)


class V2CompileJobResponse(CompileJobResponse):
    template_id: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "succeeded", "failed"]
    message: str = ""
    logs: list[str] = Field(default_factory=list)
    artifact_path: Optional[str] = None
    diagnostics: list[dict[str, object]] = Field(default_factory=list)
