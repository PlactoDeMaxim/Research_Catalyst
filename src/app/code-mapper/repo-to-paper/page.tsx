"use client";

import { useCallback, useRef, useState } from "react";
import Link from "next/link";
import styles from "./page.module.css";

const API_BASE = "http://localhost:8000/api/code-mapper/repo-to-paper";

interface JobStatus {
    job_id: string;
    phase: string;
    progress: number;
    message: string;
    error: string | null;
    result: Record<string, unknown> | null;
}

interface Section {
    section_id: string;
    title: string;
    content: string;
    citations: string[];
    word_count: number;
}

interface Citation {
    cite_key: string;
    title: string;
    authors: string[];
    year: number;
    venue: string;
    doi: string | null;
    verified: boolean;
    verification_layers: string[];
    relevance_score: number;
}

const PIPELINE_STEPS = [
    { phase: "analyzing", label: "Analyze" },
    { phase: "citing", label: "Cite" },
    { phase: "generating", label: "Write" },
    { phase: "refining", label: "Refine" },
    { phase: "exporting", label: "Export" },
];

export default function RepoToPaperPage() {
    const [url, setUrl] = useState("");
    const [paperStyle, setPaperStyle] = useState("generic");
    const [outputFormats, setOutputFormats] = useState<string[]>(["latex", "word"]);
    const [jobId, setJobId] = useState<string | null>(null);
    const [status, setStatus] = useState<JobStatus | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());
    const eventSourceRef = useRef<EventSource | null>(null);

    const handleSubmit = useCallback(async (e: React.FormEvent) => {
        e.preventDefault();
        if (!url.trim()) return;

        setError(null);
        setStatus(null);
        setExpandedSections(new Set());

        try {
            const resp = await fetch(`${API_BASE}/analyze`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    github_url: url.trim(),
                    paper_style: paperStyle,
                    output_formats: outputFormats,
                }),
            });
            if (!resp.ok) {
                const data = await resp.json().catch(() => ({}));
                throw new Error(data.detail || `Request failed: ${resp.status}`);
            }
            const data = await resp.json();
            setJobId(data.job_id);
            startSSE(data.job_id);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Request failed");
        }
    }, [url, paperStyle, outputFormats]);

    const startSSE = useCallback((id: string) => {
        if (eventSourceRef.current) eventSourceRef.current.close();

        const es = new EventSource(`${API_BASE}/stream/${id}`);
        eventSourceRef.current = es;

        es.addEventListener("progress", (e) => {
            setStatus(JSON.parse(e.data));
        });

        es.addEventListener("done", (e) => {
            setStatus(JSON.parse(e.data));
            es.close();
        });

        es.addEventListener("error", () => {
            es.close();
            pollStatus(id);
        });
    }, []);

    const pollStatus = useCallback(async (id: string) => {
        const poll = async () => {
            try {
                const resp = await fetch(`${API_BASE}/status/${id}`);
                if (!resp.ok) return;
                const data: JobStatus = await resp.json();
                setStatus(data);
                if (data.phase !== "completed" && data.phase !== "failed") {
                    setTimeout(poll, 2000);
                }
            } catch {
                setTimeout(poll, 3000);
            }
        };
        poll();
    }, []);

    const toggleSection = (id: string) => {
        setExpandedSections((prev) => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id); else next.add(id);
            return next;
        });
    };

    const toggleFormat = (fmt: string) => {
        setOutputFormats((prev) =>
            prev.includes(fmt) ? prev.filter((f) => f !== fmt) : [...prev, fmt]
        );
    };

    const isComplete = status?.phase === "completed";
    const isFailed = status?.phase === "failed";
    const result = status?.result as Record<string, unknown> | null;
    const sections = (result?.sections as Section[]) || [];
    const citations = (result?.citations as Citation[]) || [];
    const currentPhaseIdx = PIPELINE_STEPS.findIndex((s) => s.phase === status?.phase);

    return (
        <div>
            <div className={`${styles.header} animate-in`}>
                <div>
                    <Link href="/code-mapper" style={{ fontSize: "0.8rem", color: "var(--text-muted)", textDecoration: "none" }}>
                        &larr; Code Mapper
                    </Link>
                    <h1>Repo &rarr; Paper</h1>
                    <p className={styles.subtitle}>
                        Generate an academic research paper from a GitHub repository.
                    </p>
                </div>
            </div>

            {error && (
                <div className={`${styles.errorBanner} animate-in`}>
                    <span>&#9888;&#65039;</span>
                    <span>{error}</span>
                    <button className="btn btn-secondary" onClick={() => setError(null)} style={{ marginLeft: "auto", fontSize: "0.78rem" }}>
                        Dismiss
                    </button>
                </div>
            )}

            {/* Input form */}
            {!jobId && (
                <form onSubmit={handleSubmit} className={`${styles.inputForm} animate-in`}>
                    <div className={styles.urlInputWrapper}>
                        <input
                            type="text"
                            className={styles.urlInput}
                            placeholder="https://github.com/user/repository"
                            value={url}
                            onChange={(e) => setUrl(e.target.value)}
                            required
                        />
                    </div>
                    <div className={styles.optionsRow}>
                        <select
                            className={styles.selectInput}
                            value={paperStyle}
                            onChange={(e) => setPaperStyle(e.target.value)}
                        >
                            <option value="generic">Generic</option>
                            <option value="neurips">NeurIPS</option>
                            <option value="icml">ICML</option>
                            <option value="arxiv">arXiv</option>
                        </select>
                        <label style={{ fontSize: "0.82rem", display: "flex", alignItems: "center", gap: "4px" }}>
                            <input
                                type="checkbox"
                                checked={outputFormats.includes("latex")}
                                onChange={() => toggleFormat("latex")}
                            />
                            LaTeX
                        </label>
                        <label style={{ fontSize: "0.82rem", display: "flex", alignItems: "center", gap: "4px" }}>
                            <input
                                type="checkbox"
                                checked={outputFormats.includes("word")}
                                onChange={() => toggleFormat("word")}
                            />
                            Word
                        </label>
                        <button type="submit" className="btn btn-primary">
                            Generate Paper
                        </button>
                    </div>
                </form>
            )}

            {/* Progress */}
            {status && !isComplete && !isFailed && (
                <div className={`${styles.progressCard} animate-in`}>
                    <div className={styles.progressTitle}>Generating paper&hellip;</div>
                    <div className={styles.progressBarOuter}>
                        <div className={styles.progressBarInner} style={{ width: `${status.progress}%` }} />
                    </div>
                    <div className={styles.progressMessage}>{status.message}</div>
                    <div className={styles.progressSteps}>
                        {PIPELINE_STEPS.map((step, i) => {
                            const isDone = i < currentPhaseIdx;
                            const isActive = i === currentPhaseIdx;
                            return (
                                <span
                                    key={step.phase}
                                    className={`${styles.step} ${isActive ? styles.stepActive : ""} ${isDone ? styles.stepDone : ""}`}
                                >
                                    {isDone ? "✓" : isActive ? "●" : "○"} {step.label}
                                </span>
                            );
                        })}
                    </div>
                </div>
            )}

            {isFailed && (
                <div className={`${styles.errorBanner} animate-in`}>
                    <span>&#10060;</span>
                    <span>Pipeline failed: {status?.error || status?.message || "Unknown error"}</span>
                    <button className="btn btn-primary" onClick={() => { setJobId(null); setStatus(null); }} style={{ marginLeft: "auto", fontSize: "0.78rem" }}>
                        Try again
                    </button>
                </div>
            )}

            {/* Results */}
            {isComplete && result && (
                <div className={styles.resultsArea}>
                    {/* Paper sections */}
                    {sections.map((sec) => (
                        <div key={sec.section_id} className={`${styles.sectionCard} animate-in`}>
                            <div
                                className={styles.sectionHeader}
                                onClick={() => toggleSection(sec.section_id)}
                            >
                                <span className={styles.sectionTitle}>
                                    {expandedSections.has(sec.section_id) ? "▾" : "▸"}{" "}
                                    {sec.title}
                                </span>
                                <span className={styles.wordCount}>
                                    {sec.word_count} words &middot; {sec.citations.length} citations
                                </span>
                            </div>
                            {expandedSections.has(sec.section_id) && (
                                <div className={styles.sectionBody}>{sec.content}</div>
                            )}
                        </div>
                    ))}

                    {/* Citations */}
                    {citations.length > 0 && (
                        <div className={styles.citationsPanel}>
                            <div className={styles.citationsHeader}>
                                <span className={styles.citationsTitle}>
                                    References ({citations.length})
                                </span>
                            </div>
                            <div className={styles.citationsList}>
                                {citations.map((c) => (
                                    <div key={c.cite_key} className={styles.citationItem}>
                                        <span className={styles.citeKey}>[{c.cite_key}]</span>
                                        <span className={styles.citeInfo}>
                                            {c.authors.slice(0, 3).join(", ")}
                                            {c.authors.length > 3 && " et al."}
                                            {" "}&mdash; <em>{c.title}</em>
                                            {c.venue && `. ${c.venue}`}
                                            {c.year > 0 && ` (${c.year})`}
                                        </span>
                                        <span className={`${styles.verifiedBadge} ${c.verified ? styles.verified : styles.unverified}`}>
                                            {c.verified ? `✓ ${c.verification_layers.length} layers` : "unverified"}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Download bar */}
                    <div className={styles.downloadBar}>
                        {outputFormats.includes("latex") && (
                            <a
                                href={`${API_BASE}/download/${jobId}?format=latex`}
                                className="btn btn-primary"
                                download
                            >
                                &#11015; Download LaTeX
                            </a>
                        )}
                        {outputFormats.includes("word") && (
                            <a
                                href={`${API_BASE}/download/${jobId}?format=word`}
                                className="btn btn-primary"
                                download
                            >
                                &#11015; Download Word
                            </a>
                        )}
                        <button
                            className="btn btn-secondary"
                            onClick={() => { setJobId(null); setStatus(null); setExpandedSections(new Set()); }}
                        >
                            Analyze another repo
                        </button>
                    </div>
                </div>
            )}

            {/* Initial state */}
            {!jobId && !error && (
                <div className="empty-state animate-in" style={{ marginTop: "var(--space-xl)" }}>
                    <div className="empty-state-icon">&#128218;</div>
                    <h3>How it works</h3>
                    <p>
                        1. Enter a GitHub URL &rarr; 2. AI analyzes the repo &rarr;
                        3. Literature search + citation verification &rarr;
                        4. Section-by-section paper writing with 2-pass refinement &rarr;
                        5. Export as LaTeX and/or Word
                    </p>
                </div>
            )}
        </div>
    );
}
