"""
Plagiarism Check models.

The module stores scan jobs locally and enriches them as provider status/report
polls complete.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


JobStatus = Literal[
    "draft",
    "submitting",
    "processing",
    "completed",
    "failed",
]

JobInputType = Literal["text", "file"]


class TextScanRequest(BaseModel):
    text: str = Field(min_length=80, max_length=200000)
    filename: str = Field(default="submission.txt", max_length=255)
    language: str | None = Field(default=None, max_length=10)
    sandbox: bool = False
    sensitivity_level: int = Field(default=3, ge=1, le=5)
    ai_sensitivity: int = Field(default=2, ge=1, le=3)
    explain_ai: bool = False


class ScanAlert(BaseModel):
    category: int | None = None
    code: str | None = None
    title: str | None = None
    message: str | None = None
    helpLink: str | None = None
    severity: int | None = None
    additionalData: str | None = None


class MatchSource(BaseModel):
    id: str | int | None = None
    title: str | None = None
    url: str | None = None
    matchedWords: int = 0
    introduction: str | None = None
    sourceType: str = "unknown"
    similarityScore: float | None = None
    overlapSnippet: str | None = None


class PlagiarismSummary(BaseModel):
    aggregatedScore: float = 0.0
    identicalWords: int = 0
    minorChangedWords: int = 0
    relatedMeaningWords: int = 0
    topSources: list[MatchSource] = Field(default_factory=list)


class AiClassification(BaseModel):
    classification: int | None = None
    classificationLabel: str | None = None
    probability: float | None = None
    textPreview: str | None = None


class AiDetectionSummary(BaseModel):
    overall: str | None = None
    humanSections: int = 0
    aiSections: int = 0
    sections: list[AiClassification] = Field(default_factory=list)
    raw: dict[str, Any] | None = None


class SectionFinding(BaseModel):
    title: str
    textPreview: str
    similarityScore: float
    riskLabel: str
    matchedSource: MatchSource | None = None
    overlappingPhrases: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class ScanJob(BaseModel):
    id: str
    scan_id: str
    status: JobStatus
    input_type: JobInputType
    filename: str
    created_at: str
    updated_at: str
    sandbox: bool = False
    text_preview: str | None = None
    webhook_status: str | None = None
    plagiarism_text_id: str | None = None
    ai_check_id: str | None = None
    error: str | None = None
    ai_detection: AiDetectionSummary | None = None
    plagiarism: PlagiarismSummary | None = None
    section_findings: list[SectionFinding] = Field(default_factory=list)
    alerts: list[ScanAlert] = Field(default_factory=list)
    scanned_document: dict[str, Any] | None = None
    webhook_payload: dict[str, Any] | None = None


class JobsListResponse(BaseModel):
    jobs: list[ScanJob] = Field(default_factory=list)


class ModuleSettingsResponse(BaseModel):
    configured: bool
    webhook_ready: bool
    backend_public_url: str | None = None
    allowed_extensions: list[str] = Field(default_factory=list)


class WebhookAckResponse(BaseModel):
    ok: bool = True
    scan_id: str
    event: str
