"use client";

import { ChangeEvent, FormEvent, useEffect, useRef, useState } from "react";
import styles from "./page.module.css";

const API = "http://localhost:8000/api/plagiarism-check";

type JobStatus = "draft" | "submitting" | "processing" | "completed" | "failed";
type JobInputType = "text" | "file";

interface AiSection {
    classification: number | null;
    classificationLabel: string | null;
    probability: number | null;
    textPreview: string | null;
}

interface AiDetectionSummary {
    overall: string | null;
    humanSections: number;
    aiSections: number;
    sections: AiSection[];
}

interface MatchSource {
    id: string | number | null;
    title: string | null;
    url: string | null;
    matchedWords: number;
    introduction: string | null;
    sourceType: string;
}

interface PlagiarismSummary {
    aggregatedScore: number;
    identicalWords: number;
    minorChangedWords: number;
    relatedMeaningWords: number;
    topSources: MatchSource[];
}

interface ScanAlert {
    category: number | null;
    code: string | null;
    title: string | null;
    message: string | null;
    severity: number | null;
    additionalData: string | null;
}

interface SectionFinding {
    title: string;
    textPreview: string;
    similarityScore: number;
    riskLabel: string;
    matchedSource: MatchSource | null;
    overlappingPhrases: string[];
    suggestions: string[];
}

interface ScanJob {
    id: string;
    scan_id: string;
    status: JobStatus;
    input_type: JobInputType;
    filename: string;
    created_at: string;
    updated_at: string;
    sandbox: boolean;
    text_preview: string | null;
    webhook_status: string | null;
    plagiarism_text_id: string | null;
    ai_check_id: string | null;
    error: string | null;
    ai_detection: AiDetectionSummary | null;
    plagiarism: PlagiarismSummary | null;
    section_findings: SectionFinding[];
    alerts: ScanAlert[];
    scanned_document?: {
        extractedTextPreview?: string | null;
    } | null;
}

function fmtDate(value: string) {
    try {
        return new Intl.DateTimeFormat("en", {
            dateStyle: "medium",
            timeStyle: "short",
        }).format(new Date(value));
    } catch {
        return value;
    }
}

function statusTone(status: JobStatus) {
    if (status === "completed") return "badge-complete";
    if (status === "failed") return "badge-review";
    if (status === "processing" || status === "submitting") return "badge-planning";
    return "badge-literature";
}

function escapeRegExp(value: string) {
    return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function renderHighlightedText(text: string, phrases: string[]) {
    const filtered = [...phrases]
        .filter((phrase) => phrase.trim().length > 0)
        .sort((a, b) => b.length - a.length);

    if (!filtered.length) {
        return text;
    }

    const pattern = new RegExp(`(${filtered.map(escapeRegExp).join("|")})`, "gi");
    const parts = text.split(pattern);

    return parts.map((part, index) => {
        const matched = filtered.some((phrase) => phrase.toLowerCase() === part.toLowerCase());
        if (!matched) {
            return <span key={`${part}-${index}`}>{part}</span>;
        }
        return (
            <mark key={`${part}-${index}`} className={styles.highlight}>
                {part}
            </mark>
        );
    });
}

export default function PlagiarismCheckPage() {
    const [mode, setMode] = useState<JobInputType>("text");
    const [text, setText] = useState("");
    const [filename, setFilename] = useState<string>("submission.txt");
    const [file, setFile] = useState<File | null>(null);
    const [sandbox, setSandbox] = useState(false);
    const [sensitivity, setSensitivity] = useState(3);
    const [jobs, setJobs] = useState<ScanJob[]>([]);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [activeJobId, setActiveJobId] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement | null>(null);

    async function loadJobs() {
        try {
            const res = await fetch(`${API}/jobs`);
            const data = await res.json();
            const nextJobs = data.jobs || [];
            setJobs(nextJobs);
            setActiveJobId((current) => current || nextJobs[0]?.id || null);
        } catch {
            /* ignore */
        }
    }

    useEffect(() => {
        loadJobs();
        const interval = window.setInterval(loadJobs, 8000);
        return () => window.clearInterval(interval);
    }, []);

    const activeJob = jobs.find((job) => job.id === activeJobId) || jobs[0] || null;
    const recentJobs = jobs.slice(0, 3);

    async function handleTextSubmit(e: FormEvent) {
        e.preventDefault();
        if (text.trim().length < 80) {
            setError("Paste at least 80 characters before starting a scan.");
            return;
        }
        setSubmitting(true);
        setError(null);
        try {
            const res = await fetch(`${API}/scan/text`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    text,
                    filename,
                    sandbox,
                    sensitivity_level: sensitivity,
                }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Failed to submit text scan");
            await loadJobs();
            setActiveJobId(data.id);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Failed to submit text scan");
        } finally {
            setSubmitting(false);
        }
    }

    async function handleFileSubmit(e: FormEvent) {
        e.preventDefault();
        if (!file) {
            setError("Choose a PDF, DOC, DOCX, or TXT file.");
            return;
        }
        setSubmitting(true);
        setError(null);
        try {
            const form = new FormData();
            form.append("file", file);
            form.append("sandbox", String(sandbox));
            form.append("sensitivity_level", String(sensitivity));
            const res = await fetch(`${API}/scan/file`, {
                method: "POST",
                body: form,
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Failed to submit file scan");
            await loadJobs();
            setActiveJobId(data.id);
            setFile(null);
            if (fileInputRef.current) fileInputRef.current.value = "";
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Failed to submit file scan");
        } finally {
            setSubmitting(false);
        }
    }

    async function refreshJob(jobId: string) {
        setError(null);
        try {
            const res = await fetch(`${API}/jobs/${jobId}/refresh`, { method: "POST" });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Failed to refresh scan");
            await loadJobs();
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Failed to refresh scan");
        }
    }

    function onFileChange(e: ChangeEvent<HTMLInputElement>) {
        setFile(e.target.files?.[0] || null);
    }

    return (
        <div>
            <div className="page-header animate-in">
                <h1>Plagiarism Check</h1>
                <p>Check section-level similarity against free scholarly metadata sources and get lightweight rewriting guidance.</p>
            </div>

            {error && (
                <div className={styles.errorBanner}>
                    <span>{error}</span>
                    <button className={styles.errorClose} onClick={() => setError(null)}>✕</button>
                </div>
            )}

            <div className={styles.layout}>
                <section className={`card ${styles.submitPanel}`}>
                    <div className={styles.modeToggle}>
                        <button
                            className={`${styles.modeButton} ${mode === "text" ? styles.modeButtonActive : ""}`}
                            onClick={() => setMode("text")}
                        >
                            Paste Text
                        </button>
                        <button
                            className={`${styles.modeButton} ${mode === "file" ? styles.modeButtonActive : ""}`}
                            onClick={() => setMode("file")}
                        >
                            Upload File
                        </button>
                    </div>

                    {mode === "text" ? (
                        <form className={styles.form} onSubmit={handleTextSubmit}>
                            <label className={styles.label}>
                                Submission name
                                <input className="input" value={filename ?? ""} onChange={(e) => setFilename(e.target.value ?? "")} />
                            </label>
                            <label className={styles.label}>
                                Text to analyze
                                <textarea
                                    className={`input ${styles.textarea}`}
                                    value={text}
                                    onChange={(e) => setText(e.target.value)}
                                    placeholder="Paste the draft, abstract, or section you want to verify."
                                />
                            </label>
                            <div className={styles.controls}>
                                <label className={styles.inlineLabel}>
                                    Sensitivity
                                    <input
                                        className={styles.range}
                                        type="range"
                                        min={1}
                                        max={5}
                                        value={sensitivity}
                                        onChange={(e) => setSensitivity(Number(e.target.value))}
                                    />
                                    <span>{sensitivity}</span>
                                </label>
                            </div>
                            <button className="btn btn-primary" disabled={submitting}>
                                {submitting ? "Submitting..." : "Check Text"}
                            </button>
                        </form>
                    ) : (
                        <form className={styles.form} onSubmit={handleFileSubmit}>
                            <label className={styles.label}>
                                Document
                                <input
                                    ref={fileInputRef}
                                    className="input"
                                    type="file"
                                    accept=".pdf,.doc,.docx,.txt"
                                    onChange={onFileChange}
                                />
                            </label>
                            <div className={styles.fileMeta}>
                                <span>{file ? `${file.name} • ${(file.size / 1024 / 1024).toFixed(2)} MB` : "No file selected"}</span>
                            </div>
                            <div className={styles.controls}>
                                <label className={styles.inlineLabel}>
                                    Sensitivity
                                    <input
                                        className={styles.range}
                                        type="range"
                                        min={1}
                                        max={5}
                                        value={sensitivity}
                                        onChange={(e) => setSensitivity(Number(e.target.value))}
                                    />
                                    <span>{sensitivity}</span>
                                </label>
                            </div>
                            <button className="btn btn-primary" disabled={submitting}>
                                {submitting ? "Submitting..." : "Check Document"}
                            </button>
                        </form>
                    )}
                </section>

                <section className={styles.resultsPanel}>
                    <div className={`card ${styles.detailPanel}`}>
                        {activeJob ? (
                            <>
                                <div className={styles.panelHeader}>
                                    <div>
                                        <h3>{activeJob.filename}</h3>
                                    </div>
                                    <div className={styles.detailActions}>
                                        <span className={`badge ${statusTone(activeJob.status)}`}>{activeJob.status}</span>
                                        {(activeJob.status === "processing" || activeJob.status === "failed") && (
                                            <button className="btn btn-secondary" onClick={() => refreshJob(activeJob.id)}>
                                                Refresh Scan
                                            </button>
                                        )}
                                    </div>
                                </div>

                                <div className={styles.metricsGrid}>
                                    <div className={styles.metricCard}>
                                        <span className={styles.metricLabel}>Similarity Score</span>
                                        <strong>{activeJob.plagiarism?.aggregatedScore?.toFixed(1) ?? "--"}%</strong>
                                    </div>
                                    <div className={styles.metricCard}>
                                        <span className={styles.metricLabel}>Flagged Sections</span>
                                        <strong>{activeJob.section_findings.filter((item) => item.similarityScore >= 44).length}</strong>
                                    </div>
                                    <div className={styles.metricCard}>
                                        <span className={styles.metricLabel}>Top Risk</span>
                                        <strong>{activeJob.section_findings[0]?.riskLabel || "No findings"}</strong>
                                    </div>
                                </div>

                                {activeJob.error && <div className={styles.failureBox}>{activeJob.error}</div>}

                                <div className={styles.section}>
                                    <h4>Section Findings</h4>
                                    {activeJob.section_findings.length ? (
                                        <div className={styles.sectionList}>
                                            {activeJob.section_findings.map((section, index) => (
                                                <div key={`${activeJob.id}-section-${index}`} className={styles.sectionCard}>
                                                    <div className={styles.sectionHeader}>
                                                        <span className={`badge ${section.similarityScore >= 62 ? "badge-review" : section.similarityScore >= 44 ? "badge-literature" : "badge-complete"}`}>
                                                            {section.riskLabel}
                                                        </span>
                                                        <span>{section.similarityScore.toFixed(1)}% similarity</span>
                                                    </div>
                                                    <strong>{section.title}</strong>
                                                    <p>{renderHighlightedText(section.textPreview, section.overlappingPhrases)}</p>
                                                    {section.matchedSource && (
                                                        <div className={styles.findingMeta}>
                                                            <span>Closest match: {section.matchedSource.title || "Untitled source"}</span>
                                                            {section.matchedSource.url && (
                                                                <a href={section.matchedSource.url} target="_blank" rel="noreferrer">
                                                                    Open source
                                                                </a>
                                                            )}
                                                        </div>
                                                    )}
                                                    {section.overlappingPhrases.length > 0 && (
                                                        <p className={styles.sectionIntro}>
                                                            Overlapping phrases: {section.overlappingPhrases.join(", ")}
                                                        </p>
                                                    )}
                                                    <div className={styles.suggestionList}>
                                                        {section.suggestions.map((suggestion, suggestionIndex) => (
                                                            <div key={`${activeJob.id}-section-${index}-suggestion-${suggestionIndex}`} className={styles.suggestionItem}>
                                                                {suggestion}
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    ) : (
                                        <p className={styles.sectionIntro}>No section findings stored yet.</p>
                                    )}
                                </div>

                                <div className={styles.section}>
                                    <h4>Matched Sources</h4>
                                    {activeJob.plagiarism?.topSources?.length ? (
                                        <div className={styles.sourcesList}>
                                            {activeJob.plagiarism.topSources.map((source, index) => (
                                                <div key={`${activeJob.id}-source-${index}`} className={styles.sourceRow}>
                                                    <div>
                                                        <strong>{source.title || source.url || "Untitled source"}</strong>
                                                        <p>{source.introduction || source.sourceType}</p>
                                                    </div>
                                                    <div className={styles.sourceMeta}>
                                                        <span>{source.matchedWords} words</span>
                                                        {source.url && (
                                                            <a href={source.url} target="_blank" rel="noreferrer">
                                                                Open
                                                            </a>
                                                        )}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    ) : (
                                        <p className={styles.sectionIntro}>No plagiarism source results stored yet.</p>
                                    )}
                                </div>
                            </>
                        ) : (
                            <div className="empty-state">
                                <div className="empty-state-icon">📄</div>
                                <h3>Select a scan</h3>
                                <p>The detailed plagiarism and AI results appear here.</p>
                            </div>
                        )}
                    </div>

                    <div className={`card ${styles.jobsList}`}>
                        <div className={styles.panelHeader}>
                            <h3>Recent Scans</h3>
                            <button className="btn btn-ghost" onClick={loadJobs}>Refresh</button>
                        </div>
                        {recentJobs.length === 0 ? (
                            <div className="empty-state">
                                <div className="empty-state-icon">🛡️</div>
                                <h3>No scans yet</h3>
                                <p>Submit text or a document to start the first plagiarism check.</p>
                            </div>
                        ) : (
                            <div className={styles.jobCards}>
                                {recentJobs.map((job) => (
                                    <button
                                        key={job.id}
                                        className={`${styles.jobCard} ${activeJob?.id === job.id ? styles.jobCardActive : ""}`}
                                        onClick={() => setActiveJobId(job.id)}
                                    >
                                        <div className={styles.jobTopline}>
                                            <span className={`badge ${statusTone(job.status)}`}>{job.status}</span>
                                            <span className={styles.jobType}>{job.input_type}</span>
                                        </div>
                                        <h4>{job.filename}</h4>
                                        <p>{job.text_preview || "Document submission"}</p>
                                        <span className={styles.jobTime}>{fmtDate(job.updated_at)}</span>
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>
                </section>
            </div>
        </div>
    );
}
