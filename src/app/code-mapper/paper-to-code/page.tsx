"use client";

import { useCallback, useRef, useState } from "react";
import Link from "next/link";
import styles from "./page.module.css";

const API_BASE = "http://localhost:8000/api/code-mapper/paper-to-code";

interface JobStatus {
    job_id: string;
    phase: string;
    progress: number;
    message: string;
    error: string | null;
    result: Record<string, unknown> | null;
}

const PIPELINE_STEPS = [
    { phase: "parsing", label: "Parse" },
    { phase: "extracting", label: "Extract" },
    { phase: "generating", label: "Generate" },
    { phase: "validating", label: "Validate" },
    { phase: "packaging", label: "Package" },
];

export default function PaperToCodePage() {
    const [dragOver, setDragOver] = useState(false);
    const [jobId, setJobId] = useState<string | null>(null);
    const [status, setStatus] = useState<JobStatus | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [selectedFile, setSelectedFile] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const eventSourceRef = useRef<EventSource | null>(null);

    const handleUpload = useCallback(async (file: File) => {
        setError(null);
        setStatus(null);
        setSelectedFile(null);

        const formData = new FormData();
        formData.append("file", file);

        try {
            const resp = await fetch(`${API_BASE}/upload`, {
                method: "POST",
                body: formData,
            });
            if (!resp.ok) {
                const data = await resp.json().catch(() => ({}));
                throw new Error(data.detail || `Upload failed: ${resp.status}`);
            }
            const data = await resp.json();
            setJobId(data.job_id);
            startSSE(data.job_id);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Upload failed");
        }
    }, []);

    const startSSE = useCallback((id: string) => {
        if (eventSourceRef.current) {
            eventSourceRef.current.close();
        }

        const es = new EventSource(`${API_BASE}/stream/${id}`);
        eventSourceRef.current = es;

        es.addEventListener("progress", (e) => {
            const data: JobStatus = JSON.parse(e.data);
            setStatus(data);
        });

        es.addEventListener("done", (e) => {
            const data: JobStatus = JSON.parse(e.data);
            setStatus(data);
            es.close();
        });

        es.addEventListener("error", () => {
            es.close();
            // Fall back to polling
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

    const onDrop = useCallback(
        (e: React.DragEvent) => {
            e.preventDefault();
            setDragOver(false);
            const file = e.dataTransfer.files[0];
            if (file) handleUpload(file);
        },
        [handleUpload]
    );

    const onFileSelect = useCallback(
        (e: React.ChangeEvent<HTMLInputElement>) => {
            const file = e.target.files?.[0];
            if (file) handleUpload(file);
        },
        [handleUpload]
    );

    const isComplete = status?.phase === "completed";
    const isFailed = status?.phase === "failed";
    const result = status?.result as Record<string, unknown> | null;
    const methodology = result?.methodology as Record<string, unknown> | null;
    const files = (result?.files as Array<{ path: string; content: string; language: string }>) || [];
    const validation = (result?.validation as Array<{ file_path: string; passed: boolean }>) || [];

    const currentPhaseIdx = PIPELINE_STEPS.findIndex((s) => s.phase === status?.phase);

    const previewFile = files.find((f) => f.path === selectedFile);

    return (
        <div>
            <div className={`${styles.header} animate-in`}>
                <div>
                    <Link href="/code-mapper" style={{ fontSize: "0.8rem", color: "var(--text-muted)", textDecoration: "none" }}>
                        &larr; Code Mapper
                    </Link>
                    <h1>Paper &rarr; Code</h1>
                    <p className={styles.subtitle}>
                        Upload a research paper to generate a runnable ML/DL implementation.
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

            {/* Upload zone — visible when no job is running */}
            {!jobId && (
                <div
                    className={`${styles.uploadZone} ${dragOver ? styles.uploadZoneDragOver : ""} animate-in`}
                    onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                    onDragLeave={() => setDragOver(false)}
                    onDrop={onDrop}
                    onClick={() => fileInputRef.current?.click()}
                >
                    <div className={styles.uploadIcon}>📄</div>
                    <div className={styles.uploadTitle}>
                        Drop your research paper here
                    </div>
                    <div className={styles.uploadHint}>
                        Supports PDF and Word (.docx) &mdash; ML/DL papers work best
                    </div>
                    <input
                        ref={fileInputRef}
                        type="file"
                        accept=".pdf,.docx,.doc"
                        className={styles.uploadInput}
                        onChange={onFileSelect}
                    />
                </div>
            )}

            {/* Progress tracker */}
            {status && !isComplete && !isFailed && (
                <div className={`${styles.progressCard} animate-in`}>
                    <div className={styles.progressTitle}>Generating code&hellip;</div>
                    <div className={styles.progressBarOuter}>
                        <div
                            className={styles.progressBarInner}
                            style={{ width: `${status.progress}%` }}
                        />
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

            {/* Failed state */}
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
                <>
                    <div className={`${styles.resultsGrid} animate-in`}>
                        {/* Left: Methodology */}
                        <div className={styles.resultPanel}>
                            <div className={styles.panelHeader}>
                                <span className={styles.panelTitle}>Extracted Methodology</span>
                            </div>
                            <div className={styles.panelBody}>
                                {methodology && (
                                    <>
                                        <MethodField label="Problem" value={methodology.problem_statement as string} />
                                        <MethodField label="Architecture" value={(methodology.model_architecture as Record<string, unknown>)?.description as string} />
                                        <MethodField label="Data Pipeline" value={(methodology.data_pipeline as Record<string, unknown>)?.description as string} />
                                        <MethodField label="Loss Functions" value={(methodology.loss_functions as string[])?.join(", ")} />
                                        <MethodField label="Training" value={(methodology.training_procedure as Record<string, unknown>)?.description as string} />
                                        <MethodField label="Metrics" value={(methodology.evaluation_metrics as string[])?.join(", ")} />
                                    </>
                                )}
                            </div>
                        </div>

                        {/* Right: File Tree + Code Preview */}
                        <div className={styles.resultPanel}>
                            <div className={styles.panelHeader}>
                                <span className={styles.panelTitle}>Generated Files</span>
                                <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                                    {files.length} files
                                </span>
                            </div>
                            <div className={styles.panelBody}>
                                <div className={styles.fileTree}>
                                    {files.map((f) => {
                                        const val = validation.find((v) => v.file_path === f.path);
                                        return (
                                            <div
                                                key={f.path}
                                                className={`${styles.fileEntry} ${selectedFile === f.path ? styles.fileEntryActive : ""}`}
                                                onClick={() => setSelectedFile(f.path === selectedFile ? null : f.path)}
                                            >
                                                <span className={styles.fileIcon}>
                                                    {f.language === "python" ? "🐍" : "📄"}
                                                </span>
                                                <span className={styles.fileName}>{f.path}</span>
                                                {val && (
                                                    <span className={`${styles.validBadge} ${val.passed ? styles.validPass : styles.validFail}`}>
                                                        {val.passed ? "✓" : "✗"}
                                                    </span>
                                                )}
                                            </div>
                                        );
                                    })}
                                </div>

                                {previewFile && (
                                    <pre className={styles.codePreview}>
                                        {previewFile.content}
                                    </pre>
                                )}
                            </div>
                        </div>
                    </div>

                    <div className={styles.downloadBar}>
                        <a
                            href={`${API_BASE}/download/${jobId}`}
                            className="btn btn-primary"
                            download
                        >
                            &#11015; Download Project ZIP
                        </a>
                        <button
                            className="btn btn-secondary"
                            onClick={() => { setJobId(null); setStatus(null); setSelectedFile(null); }}
                        >
                            Upload another paper
                        </button>
                    </div>
                </>
            )}

            {/* Initial state */}
            {!jobId && !error && (
                <div className="empty-state animate-in" style={{ marginTop: "var(--space-xl)" }}>
                    <div className="empty-state-icon">&#129302;</div>
                    <h3>How it works</h3>
                    <p>
                        1. Upload a paper &rarr; 2. AI extracts methodology &rarr;
                        3. Multi-phase code generation &rarr; 4. Validation &amp; fix loop &rarr;
                        5. Download runnable project
                    </p>
                </div>
            )}
        </div>
    );
}

function MethodField({ label, value }: { label: string; value?: string }) {
    if (!value) return null;
    return (
        <div className={styles.methodSection}>
            <div className={styles.methodLabel}>{label}</div>
            <div className={styles.methodValue}>{value}</div>
        </div>
    );
}
