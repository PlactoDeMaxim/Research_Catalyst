import { PAPER_EDITOR_API_BASE } from "@/lib/paperEditorApi";

async function postJson<T>(path: string, payload: unknown): Promise<T> {
    const response = await fetch(`${PAPER_EDITOR_API_BASE}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    if (!response.ok) {
        throw new Error(`Writing assistant request failed (${response.status})`);
    }
    return (await response.json()) as T;
}

export type GroundedDraftResponse = {
    drafted_text: string;
    citation_suggestions: string[];
    claim_snippets: string[];
    notes: string[];
};

export type CitationRecommendation = {
    cite_key: string;
    reason: string;
    confidence: number;
};

export type ClaimTraceItem = {
    claim: string;
    support_excerpt: string;
    confidence: number;
};

export type ManuscriptReviewResponse = {
    strengths: string[];
    weaknesses: string[];
    revision_actions: string[];
};

export type ReviewerResponseItem = {
    comment: string;
    draft_response: string;
    action_item: string;
};

export type ComplianceIssue = {
    issue: string;
    severity: string;
    fix_hint: string;
};

export type WritingAssistBundle = {
    drafted_text: string;
    autocomplete_suggestions: string[];
    citation_recommendations: CitationRecommendation[];
    claim_traces: ClaimTraceItem[];
    manuscript_review: ManuscriptReviewResponse;
    reviewer_response_plan: { responses: ReviewerResponseItem[] };
    compliance: { compliant: boolean; issues: ComplianceIssue[] };
};

export async function generateGroundedDraft(payload: {
    section_title: string;
    prompt: string;
    current_text: string;
    evidence: Array<Record<string, unknown>>;
    citations: Array<Record<string, unknown>>;
}) {
    return postJson<GroundedDraftResponse>("/v2/grounded-draft", payload);
}

export async function generateAutocomplete(payload: {
    section_title: string;
    prefix_text: string;
    evidence: Array<Record<string, unknown>>;
}) {
    return postJson<{ suggestions: string[] }>("/v2/autocomplete", payload);
}

export async function recommendCitations(payload: {
    text: string;
    bibliography_entries: string[];
    evidence: Array<Record<string, unknown>>;
}) {
    return postJson<{ recommendations: CitationRecommendation[] }>("/v2/citation-recommendations", payload);
}

export async function traceClaims(payload: {
    text: string;
    evidence: Array<Record<string, unknown>>;
}) {
    return postJson<{ traces: ClaimTraceItem[] }>("/v2/claim-trace", payload);
}

export async function reviewManuscript(payload: {
    title: string;
    abstract: string;
    sections: Array<Record<string, string>>;
}) {
    return postJson<ManuscriptReviewResponse>("/v2/manuscript-review", payload);
}

export async function createReviewerResponsePlan(payload: {
    reviewer_comments: string[];
    manuscript_context: string;
}) {
    return postJson<{ responses: ReviewerResponseItem[] }>("/v2/reviewer-response", payload);
}

export async function runComplianceCheck(payload: {
    venue: string;
    required_sections: string[];
    manuscript: string;
}) {
    return postJson<{ compliant: boolean; issues: ComplianceIssue[] }>("/v2/compliance-check", payload);
}

export async function assistWriter(payload: {
    section_title: string;
    goal: string;
    current_text: string;
    evidence: Array<Record<string, unknown>>;
    bibliography_entries: string[];
    reviewer_comments: string[];
    venue: string;
    required_sections: string[];
    all_sections: Array<Record<string, string>>;
}) {
    return postJson<WritingAssistBundle>("/v2/assist", payload);
}
