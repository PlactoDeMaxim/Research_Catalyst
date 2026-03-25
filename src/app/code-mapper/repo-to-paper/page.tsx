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

const PIPELINE_STEPS = [
    { phase: "analyzing", label: "Analyzing Repo" },
    { phase: "generating", label: "Writing Report" },
    { phase: "exporting", label: "Exporting" },
];

export default function RepoToPaperPage() {
    const [url, setUrl] = useState("");
    const [paperStyle, setPaperStyle] = useState("generic");
    const [outputFormats, setOutputFormats] = useState<string[]>(["latex", "word"]);
    const [jobId, setJobId] = useState<string | null>(null);
    const [status, setStatus] = useState<JobStatus | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [editedSections, setEditedSections] = useState<Section[]>([]);
    const [saving, setSaving] = useState(false);
    const [saveMsg, setSaveMsg] = useState<string | null>(null);
    const eventSourceRef = useRef<EventSource | null>(null);

    const handleSubmit = useCallback(async (e: React.FormEvent) => {
        e.preventDefault();
        if (!url.trim()) return;

        setError(null);
        setStatus(null);
        setEditedSections([]);
        setSaveMsg(null);

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
            const parsed = JSON.parse(e.data);
            setStatus(parsed);
            if (parsed.phase === "completed") {
                loadSections(parsed);
                es.close();
            }
        });

        es.addEventListener("done", (e) => {
            const parsed = JSON.parse(e.data);
            setStatus(parsed);
            loadSections(parsed);
            es.close();
        });

        es.addEventListener("error", () => {
            es.close();
            pollStatus(id);
        });
    }, []);

    const loadSections = (st: JobStatus) => {
        const result = st.result as Record<string, unknown> | null;
        if (result && Array.isArray(result.sections)) {
            setEditedSections(result.sections as Section[]);
        }
    };

    const pollStatus = useCallback(async (id: string) => {
        const poll = async () => {
            try {
                const resp = await fetch(`${API_BASE}/status/${id}`);
                if (!resp.ok) return;
                const data: JobStatus = await resp.json();
                setStatus(data);
                if (data.phase === "completed") {
                    loadSections(data);
                } else if (data.phase !== "failed") {
                    setTimeout(poll, 2000);
                }
            } catch {
                setTimeout(poll, 3000);
            }
        };
        poll();
    }, []);

    const updateSectionContent = (sectionId: string, content: string) => {
        setEditedSections((prev) =>
            prev.map((s) =>
                s.section_id === sectionId
                    ? { ...s, content, word_count: content.split(/\s+/).filter(Boolean).length }
                    : s
            )
        );
        setSaveMsg(null);
    };

    const handleSave = useCallback(async () => {
        if (!jobId) return;
        setSaving(true);
        setSaveMsg(null);

        try {
            const resp = await fetch(`${API_BASE}/sections/${jobId}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    sections: editedSections.map((s) => ({
                        section_id: s.section_id,
                        title: s.title,
                        content: s.content,
                    })),
                }),
            });
            if (!resp.ok) {
                const data = await resp.json().catch(() => ({}));
                throw new Error(data.detail || "Save failed");
            }
            setSaveMsg("Saved & re-exported successfully!");
        } catch (err) {
            setSaveMsg(err instanceof Error ? err.message : "Save failed");
        } finally {
            setSaving(false);
        }
    }, [jobId, editedSections]);

    const toggleFormat = (fmt: string) => {
        setOutputFormats((prev) =>
            prev.includes(fmt) ? prev.filter((f) => f !== fmt) : [...prev, fmt]
        );
    };

    const isComplete = status?.phase === "completed";
    const isFailed = status?.phase === "failed";
    const currentPhaseIdx = PIPELINE_STEPS.findIndex((s) => s.phase === status?.phase);
    const totalWords = editedSections.reduce((sum, s) => sum + s.word_count, 0);

    return (
        <div className={styles.pageContainer}>
            <div className={`${styles.header} animate-in`}>
                <div>
                    <Link href="/code-mapper" className={styles.backLink}>
                        &larr; Code Mapper
                    </Link>
                    <h1 className={styles.pageTitle}>Project Report Generator</h1>
                    <p className={styles.subtitle}>
                        Generate an editable project report from a GitHub repository.
                    </p>
                </div>
            </div>

            {error && (
                <div className={`${styles.errorBanner} animate-in`}>
                    <span>&#9888;&#65039;</span>
                    <span>{error}</span>
                    <button className={styles.btnSecondary} onClick={() => setError(null)}>
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
                            id="repo-url-input"
                        />
                    </div>
                    <div className={styles.optionsRow}>
                        <select
                            className={styles.selectInput}
                            value={paperStyle}
                            onChange={(e) => setPaperStyle(e.target.value)}
                            id="paper-style-select"
                        >
                            <option value="generic">Generic</option>
                            <option value="neurips">NeurIPS</option>
                            <option value="icml">ICML</option>
                            <option value="arxiv">arXiv</option>
                        </select>
                        <label className={styles.checkboxLabel}>
                            <input
                                type="checkbox"
                                checked={outputFormats.includes("latex")}
                                onChange={() => toggleFormat("latex")}
                            />
                            LaTeX
                        </label>
                        <label className={styles.checkboxLabel}>
                            <input
                                type="checkbox"
                                checked={outputFormats.includes("word")}
                                onChange={() => toggleFormat("word")}
                            />
                            Word
                        </label>
                        <button type="submit" className={styles.btnPrimary} id="generate-btn">
                            Generate Report
                        </button>
                    </div>
                </form>
            )}

            {/* Progress */}
            {status && !isComplete && !isFailed && (
                <div className={`${styles.progressCard} animate-in`}>
                    <div className={styles.progressTitle}>Generating report&hellip;</div>
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
                    <button className={styles.btnPrimary} onClick={() => { setJobId(null); setStatus(null); }}>
                        Try again
                    </button>
                </div>
            )}

            {/* Editable Report Editor */}
            {isComplete && editedSections.length > 0 && (
                <div className={styles.editorArea}>
                    <h1 className={styles.documentTitle}>Report AI</h1>

                    {/* Sections */}
                    {editedSections.map((sec) => (
                        <div key={sec.section_id} className={styles.sectionEditor}>
                            <div className={styles.sectionEditorHeader}>
                                <h2 className={styles.sectionTitle}>{sec.title}</h2>
                            </div>
                            <textarea
                                className={styles.sectionTextarea}
                                value={sec.content}
                                onChange={(e) => updateSectionContent(sec.section_id, e.target.value)}
                                rows={Math.max(6, Math.ceil(sec.content.length / 80))}
                                id={`section-${sec.section_id}`}
                            />
                        </div>
                    ))}

                    {/* Bottom Panel */}
                    <div className={styles.bottomPanel}>
                        <div className={styles.bottomPanelLeft}>
                            {/* Removed Autocomplete and Cite as requested */}
                        </div>
                        <div className={styles.bottomPanelCenter}>
                            <button className={styles.toolbarIconBtn} title="Format Text"><b>T</b> Text</button>
                            <div className={styles.toolbarDivider} />
                            <button className={styles.toolbarIconBtn} title="Image">🖼️</button>
                            <button className={styles.toolbarIconBtn} title="Code">&lt;&gt;</button>
                            <button className={styles.toolbarIconBtn} title="Task List">[x]</button>
                            <button className={styles.toolbarIconBtn} title="Math">Σ</button>
                            <div className={styles.toolbarDivider} />
                            <button className={styles.toolbarIconBtn} title="Undo">↩</button>
                            <button className={styles.toolbarIconBtn} title="Redo">↪</button>
                        </div>
                        <div className={styles.bottomPanelRight}>
                            <span className={styles.wordCountBadge}>{totalWords} words</span>
                            {saveMsg && (
                                <span style={{ color: '#4A56E2', marginLeft: '0.5rem' }}>{saveMsg}</span>
                            )}
                            {outputFormats.includes("word") && (
                                <a
                                    href={`${API_BASE}/download/${jobId}?format=word`}
                                    className={styles.secondaryActionBtn}
                                    download
                                    id="download-word-btn"
                                    style={{ marginLeft: '0.5rem' }}
                                >
                                    📥 Word
                                </a>
                            )}
                            {outputFormats.includes("latex") && (
                                <a
                                    href={`${API_BASE}/download/${jobId}?format=latex`}
                                    className={styles.secondaryActionBtn}
                                    download
                                    id="download-latex-btn"
                                    style={{ marginLeft: '0.5rem' }}
                                >
                                    📥 LaTeX
                                </a>
                            )}
                            <button
                                className={styles.primaryActionBtn}
                                onClick={handleSave}
                                disabled={saving}
                                id="save-btn"
                                style={{ marginLeft: '0.5rem' }}
                            >
                                {saving ? "Saving…" : "Save Changes"}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Initial state */}
            {!jobId && !error && (
                <div className={styles.emptyState}>
                    <div className={styles.emptyIcon}>📄</div>
                    <h3>How it works</h3>
                    <p>
                        1. Enter a GitHub URL &rarr; 2. AI analyzes the repo &rarr;
                        3. Report generated with editable sections &rarr;
                        4. Edit in-place, then download as LaTeX / Word
                    </p>
                </div>
            )}
        </div>
    );
}
