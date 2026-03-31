from __future__ import annotations

from pydantic import BaseModel, Field


class GroundedDraftRequest(BaseModel):
    project_id: str | None = None
    section_title: str
    prompt: str = ""
    current_text: str = ""
    evidence: list[dict] = Field(default_factory=list)
    citations: list[dict] = Field(default_factory=list)


class GroundedDraftResponse(BaseModel):
    drafted_text: str
    citation_suggestions: list[str] = Field(default_factory=list)
    claim_snippets: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class AutocompleteRequest(BaseModel):
    project_id: str | None = None
    section_title: str = ""
    prefix_text: str = Field(min_length=3)
    evidence: list[dict] = Field(default_factory=list)


class AutocompleteResponse(BaseModel):
    suggestions: list[str] = Field(default_factory=list)


class CitationRecommendationRequest(BaseModel):
    project_id: str | None = None
    text: str
    bibliography_entries: list[str] = Field(default_factory=list)
    evidence: list[dict] = Field(default_factory=list)


class CitationRecommendation(BaseModel):
    cite_key: str
    reason: str
    confidence: float


class CitationRecommendationResponse(BaseModel):
    recommendations: list[CitationRecommendation] = Field(default_factory=list)


class ClaimTraceRequest(BaseModel):
    project_id: str | None = None
    text: str
    evidence: list[dict] = Field(default_factory=list)


class ClaimTraceItem(BaseModel):
    claim: str
    support_excerpt: str
    confidence: float


class ClaimTraceResponse(BaseModel):
    traces: list[ClaimTraceItem] = Field(default_factory=list)


class ManuscriptReviewRequest(BaseModel):
    title: str = ""
    abstract: str = ""
    sections: list[dict] = Field(default_factory=list)


class ManuscriptReviewResponse(BaseModel):
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    revision_actions: list[str] = Field(default_factory=list)


class ReviewerResponseRequest(BaseModel):
    reviewer_comments: list[str] = Field(default_factory=list)
    manuscript_context: str = ""


class ReviewerResponseItem(BaseModel):
    comment: str
    draft_response: str
    action_item: str


class ReviewerResponsePlan(BaseModel):
    responses: list[ReviewerResponseItem] = Field(default_factory=list)


class ComplianceCheckRequest(BaseModel):
    venue: str = ""
    required_sections: list[str] = Field(default_factory=list)
    manuscript: str = ""


class ComplianceIssue(BaseModel):
    issue: str
    severity: str
    fix_hint: str


class ComplianceCheckResponse(BaseModel):
    compliant: bool
    issues: list[ComplianceIssue] = Field(default_factory=list)


class WritingAssistRequest(BaseModel):
    project_id: str | None = None
    section_title: str = ""
    goal: str = ""
    current_text: str = ""
    evidence: list[dict] = Field(default_factory=list)
    bibliography_entries: list[str] = Field(default_factory=list)
    reviewer_comments: list[str] = Field(default_factory=list)
    venue: str = "IEEE"
    required_sections: list[str] = Field(default_factory=lambda: ["Introduction", "Method", "Results", "Conclusion"])
    all_sections: list[dict] = Field(default_factory=list)


class WritingAssistResponse(BaseModel):
    drafted_text: str
    autocomplete_suggestions: list[str] = Field(default_factory=list)
    citation_recommendations: list[CitationRecommendation] = Field(default_factory=list)
    claim_traces: list[ClaimTraceItem] = Field(default_factory=list)
    manuscript_review: ManuscriptReviewResponse
    reviewer_response_plan: ReviewerResponsePlan
    compliance: ComplianceCheckResponse
