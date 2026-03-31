"use client";

import { useMemo, useState } from "react";
import styles from "../editor-v2.module.css";
import {
    assistWriter,
    createReviewerResponsePlan,
    generateAutocomplete,
    generateGroundedDraft,
    recommendCitations,
    reviewManuscript,
    runComplianceCheck,
    traceClaims,
    type CitationRecommendation,
    type ClaimTraceItem,
    type ComplianceIssue,
    type ReviewerResponseItem,
} from "./writingAssistantClient";

type WritingAssistantPanelProps = {
    currentSectionTitle: string;
    currentText: string;
    allSections: Array<{ title: string; content: string }>;
    bibContent: string;
    onApplyText: (nextText: string) => void;
    onInsertCitation: (key: string) => void;
};

function extractBibEntries(raw: string): string[] {
    return raw
        .split("@")
        .map((chunk) => chunk.trim())
        .filter(Boolean)
        .map((chunk) => `@${chunk}`);
}

function extractFirstAbstract(text: string): string {
    const match = text.match(/\\begin\{abstract\}([\s\S]*?)\\end\{abstract\}/i);
    return match?.[1]?.trim() ?? "";
}

export default function WritingAssistantPanel({
    currentSectionTitle,
    currentText,
    allSections,
    bibContent,
    onApplyText,
    onInsertCitation,
}: WritingAssistantPanelProps) {
    const [loading, setLoading] = useState(false);
    const [assistGoal, setAssistGoal] = useState("");
    const [venue, setVenue] = useState("IEEE");
    const [reviewerCommentText, setReviewerCommentText] = useState("");
    const [showAdvanced, setShowAdvanced] = useState(false);
    const [draftText, setDraftText] = useState("");
    const [autocompleteSuggestions, setAutocompleteSuggestions] = useState<string[]>([]);
    const [citationRecs, setCitationRecs] = useState<CitationRecommendation[]>([]);
    const [claimTraces, setClaimTraces] = useState<ClaimTraceItem[]>([]);
    const [reviewSummary, setReviewSummary] = useState<{
        strengths: string[];
        weaknesses: string[];
        revision_actions: string[];
    } | null>(null);
    const [reviewerResponses, setReviewerResponses] = useState<ReviewerResponseItem[]>([]);
    const [compliance, setCompliance] = useState<{ compliant: boolean; issues: ComplianceIssue[] } | null>(null);
    const [error, setError] = useState<string | null>(null);

    const evidence = useMemo(
        () =>
            allSections
                .filter((section) => section.content.trim().length > 0)
                .slice(0, 6)
                .map((section) => ({
                    title: section.title,
                    excerpt: section.content.slice(0, 380),
                })),
        [allSections]
    );
    const bibliographyEntries = useMemo(() => extractBibEntries(bibContent), [bibContent]);
    const reviewerComments = useMemo(
        () =>
            reviewerCommentText
                .split(/\r?\n/)
                .map((line) => line.trim())
                .filter(Boolean),
        [reviewerCommentText]
    );

    const withGuard = async (fn: () => Promise<void>) => {
        setLoading(true);
        setError(null);
        try {
            await fn();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Writing assistant action failed.");
        } finally {
            setLoading(false);
        }
    };

    const runSmartAssist = () =>
        void withGuard(async () => {
            const result = await assistWriter({
                section_title: currentSectionTitle || "Section",
                goal:
                    assistGoal.trim() ||
                    `Continue improving the ${currentSectionTitle || "section"} with concise, evidence-grounded writing.`,
                current_text: currentText,
                evidence,
                bibliography_entries: bibliographyEntries,
                reviewer_comments: reviewerComments,
                venue,
                required_sections: ["Introduction", "Method", "Results", "Conclusion"],
                all_sections: allSections,
            });

            setDraftText(result.drafted_text);
            setAutocompleteSuggestions(result.autocomplete_suggestions);
            setCitationRecs(result.citation_recommendations);
            setClaimTraces(result.claim_traces);
            setReviewSummary(result.manuscript_review);
            setCompliance(result.compliance);
            setReviewerResponses(result.reviewer_response_plan.responses);
        });

    return (
        <div className={styles.writingAssistantRoot}>
            <div className={styles.writingAssistantHeader}>
                <div>
                    <div className={styles.writingAssistantTitle}>Writing Copilot (Phase 3)</div>
                    <div className={styles.writingAssistantMeta}>Section: {currentSectionTitle || "Current Editor Context"}</div>
                </div>
            </div>

            <div className={styles.writingAssistantControls}>
                <input
                    className={styles.writingAssistantInput}
                    placeholder="What do you want to improve? (optional)"
                    value={assistGoal}
                    onChange={(e) => setAssistGoal(e.target.value)}
                />
                <div className={styles.writingAssistantActionRow}>
                    <button className="btn btn-primary" disabled={loading} onClick={runSmartAssist}>
                        {loading ? "Working..." : "Assist Me"}
                    </button>
                    <button
                        className="btn btn-secondary"
                        disabled={loading || autocompleteSuggestions.length === 0}
                        onClick={() => onApplyText(autocompleteSuggestions[0] ?? currentText)}
                    >
                        Apply Best Continuation
                    </button>
                    <button
                        className="btn btn-secondary"
                        disabled={loading || citationRecs.length === 0}
                        onClick={() => {
                            const top = citationRecs[0];
                            if (top) onInsertCitation(top.cite_key);
                        }}
                    >
                        Insert Top Citation
                    </button>
                    <button className="btn btn-ghost" disabled={loading} onClick={() => setShowAdvanced((v) => !v)}>
                        {showAdvanced ? "Hide Advanced" : "Show Advanced"}
                    </button>
                </div>
            </div>

            <div className={styles.writingAssistantControls}>
                <textarea
                    className={styles.writingAssistantTextarea}
                    placeholder="Reviewer comments (optional, one per line)"
                    value={reviewerCommentText}
                    onChange={(e) => setReviewerCommentText(e.target.value)}
                />
                <div className={styles.writingAssistantActionRow}>
                    <input
                        className={styles.writingAssistantInput}
                        style={{ maxWidth: "180px" }}
                        value={venue}
                        onChange={(e) => setVenue(e.target.value)}
                        placeholder="Venue (e.g. IEEE)"
                    />
                </div>
            </div>

            {showAdvanced && (
                <div className={styles.writingAssistantControls}>
                    <div className={styles.writingAssistantMeta}>Advanced controls</div>
                    <div className={styles.writingAssistantActionRow}>
                        <button
                            className="btn btn-secondary"
                            disabled={loading}
                            onClick={() =>
                                void withGuard(async () => {
                                    const data = await generateAutocomplete({
                                        section_title: currentSectionTitle || "Section",
                                        prefix_text: currentText.slice(-320) || "Continue this section",
                                        evidence,
                                    });
                                    setAutocompleteSuggestions(data.suggestions);
                                })
                            }
                        >
                            Autocomplete
                        </button>
                        <button
                            className="btn btn-secondary"
                            disabled={loading}
                            onClick={() =>
                                void withGuard(async () => {
                                    const data = await recommendCitations({
                                        text: currentText,
                                        bibliography_entries: bibliographyEntries,
                                        evidence,
                                    });
                                    setCitationRecs(data.recommendations);
                                })
                            }
                        >
                            Citation Recs
                        </button>
                        <button
                            className="btn btn-secondary"
                            disabled={loading}
                            onClick={() =>
                                void withGuard(async () => {
                                    const data = await traceClaims({
                                        text: currentText,
                                        evidence,
                                    });
                                    setClaimTraces(data.traces);
                                })
                            }
                        >
                            Claim Trace
                        </button>
                        <button
                            className="btn btn-secondary"
                            disabled={loading}
                            onClick={() =>
                                void withGuard(async () => {
                                    const data = await reviewManuscript({
                                        title: allSections[0]?.title || "Manuscript",
                                        abstract: extractFirstAbstract(currentText),
                                        sections: allSections,
                                    });
                                    setReviewSummary(data);
                                })
                            }
                        >
                            Manuscript Review
                        </button>
                        <button
                            className="btn btn-secondary"
                            disabled={loading}
                            onClick={() =>
                                void withGuard(async () => {
                                    const data = await createReviewerResponsePlan({
                                        reviewer_comments: reviewerComments,
                                        manuscript_context: currentText.slice(0, 1200),
                                    });
                                    setReviewerResponses(data.responses);
                                })
                            }
                        >
                            Reviewer Response Plan
                        </button>
                        <button
                            className="btn btn-secondary"
                            disabled={loading}
                            onClick={() =>
                                void withGuard(async () => {
                                    const data = await runComplianceCheck({
                                        venue,
                                        required_sections: ["Introduction", "Method", "Results", "Conclusion"],
                                        manuscript: currentText,
                                    });
                                    setCompliance(data);
                                })
                            }
                        >
                            Compliance Check
                        </button>
                    </div>
                </div>
            )}

            {error && <div className={styles.writingAssistantError}>{error}</div>}

            <div className={styles.writingAssistantPanels}>
                {draftText && (
                    <div className={styles.writingAssistantPanel}>
                        <h4>Grounded Draft</h4>
                        <pre className={styles.writingAssistantPre}>{draftText}</pre>
                        <button className="btn btn-primary" onClick={() => onApplyText(draftText)}>
                            Apply Draft to Editor
                        </button>
                    </div>
                )}

                {autocompleteSuggestions.length > 0 && (
                    <div className={styles.writingAssistantPanel}>
                        <h4>Autocomplete Suggestions</h4>
                        <div className={styles.writingAssistantList}>
                            {autocompleteSuggestions.map((item) => (
                                <button key={item} className={styles.writingAssistantSuggestion} onClick={() => onApplyText(item)}>
                                    {item}
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {citationRecs.length > 0 && (
                    <div className={styles.writingAssistantPanel}>
                        <h4>Citation Recommendations</h4>
                        <div className={styles.writingAssistantList}>
                            {citationRecs.map((item) => (
                                <div key={item.cite_key} className={styles.writingAssistantRow}>
                                    <div>
                                        <strong>{item.cite_key}</strong> ({(item.confidence * 100).toFixed(0)}%)
                                        <div className={styles.writingAssistantMeta}>{item.reason}</div>
                                    </div>
                                    <button className="btn btn-secondary" onClick={() => onInsertCitation(item.cite_key)}>
                                        Insert
                                    </button>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {claimTraces.length > 0 && (
                    <div className={styles.writingAssistantPanel}>
                        <h4>Claim Traceability</h4>
                        <div className={styles.writingAssistantList}>
                            {claimTraces.map((item, index) => (
                                <div key={`${item.claim}-${index}`} className={styles.writingAssistantRowBlock}>
                                    <div><strong>Claim:</strong> {item.claim}</div>
                                    <div><strong>Support:</strong> {item.support_excerpt || "No supporting excerpt in provided evidence."}</div>
                                    <div className={styles.writingAssistantMeta}>Confidence {(item.confidence * 100).toFixed(0)}%</div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {reviewSummary && (
                    <div className={styles.writingAssistantPanel}>
                        <h4>Manuscript Review</h4>
                        <div><strong>Strengths</strong></div>
                        <ul className={styles.writingAssistantUl}>{reviewSummary.strengths.map((item) => <li key={item}>{item}</li>)}</ul>
                        <div><strong>Weaknesses</strong></div>
                        <ul className={styles.writingAssistantUl}>{reviewSummary.weaknesses.map((item) => <li key={item}>{item}</li>)}</ul>
                        <div><strong>Revision Actions</strong></div>
                        <ul className={styles.writingAssistantUl}>{reviewSummary.revision_actions.map((item) => <li key={item}>{item}</li>)}</ul>
                    </div>
                )}

                {reviewerResponses.length > 0 && (
                    <div className={styles.writingAssistantPanel}>
                        <h4>Reviewer Response Plan</h4>
                        <div className={styles.writingAssistantList}>
                            {reviewerResponses.map((item, index) => (
                                <div key={`${item.comment}-${index}`} className={styles.writingAssistantRowBlock}>
                                    <div><strong>Comment:</strong> {item.comment}</div>
                                    <div><strong>Draft response:</strong> {item.draft_response}</div>
                                    <div><strong>Action:</strong> {item.action_item}</div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {compliance && (
                    <div className={styles.writingAssistantPanel}>
                        <h4>Compliance Check</h4>
                        <div className={styles.writingAssistantMeta}>
                            Status: {compliance.compliant ? "Compliant" : "Issues found"}
                        </div>
                        <div className={styles.writingAssistantList}>
                            {compliance.issues.map((item) => (
                                <div key={`${item.issue}-${item.severity}`} className={styles.writingAssistantRowBlock}>
                                    <div><strong>{item.issue}</strong> ({item.severity})</div>
                                    <div>{item.fix_hint}</div>
                                </div>
                            ))}
                            {compliance.issues.length === 0 && <div>No compliance issues detected.</div>}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
