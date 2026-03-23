"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import styles from "./page.module.css";

type CitationFormat = "APA" | "MLA" | "IEEE" | "Chicago";

interface Project {
    id: string;
    title: string;
    description: string;
}

interface CitationRecord {
    id: string;
    citation_text: string;
    csl_json: string;
    project_id: string;
    created_at: string;
}

interface GeneratedCitation {
    citation_text: string;
    csl_json: Record<string, unknown>;
    metadata: {
        title: string;
        authors: string[];
        year: string;
        publisher?: string;
        url: string;
        doi?: string;
    };
    in_text_citation: string;
}

const FORMATS: CitationFormat[] = ["APA", "MLA", "IEEE", "Chicago"];
const API = "http://localhost:8000/api/citation-manager";

export default function CitationsPage() {
    const [projects, setProjects] = useState<Project[]>([]);
    const [selectedProjectId, setSelectedProjectId] = useState("");
    const [citations, setCitations] = useState<CitationRecord[]>([]);

    const [sourceUrl, setSourceUrl] = useState("");
    const [format, setFormat] = useState<CitationFormat>("APA");
    const [generated, setGenerated] = useState<GeneratedCitation | null>(null);
    const [manualCitation, setManualCitation] = useState("");

    const [newProjectTitle, setNewProjectTitle] = useState("");
    const [loadingProjects, setLoadingProjects] = useState(true);
    const [loadingCitations, setLoadingCitations] = useState(false);
    const [generating, setGenerating] = useState(false);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    const fetchProjects = useCallback(async () => {
        setLoadingProjects(true);
        try {
            const response = await fetch(`${API}/projects`);
            if (!response.ok) throw new Error("Failed to fetch projects");
            const data: { projects: Project[] } = await response.json();
            setProjects(data.projects);
            setSelectedProjectId((current) => current || data.projects[0]?.id || "");
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Failed to load projects");
        } finally {
            setLoadingProjects(false);
        }
    }, []);

    const fetchCitations = useCallback(async (projectId: string) => {
        if (!projectId) {
            setCitations([]);
            return;
        }

        setLoadingCitations(true);
        try {
            const response = await fetch(`${API}/citations?project_id=${projectId}`);
            if (!response.ok) throw new Error("Failed to fetch citations");
            const data: { citations: CitationRecord[] } = await response.json();
            setCitations(data.citations);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Failed to load citations");
        } finally {
            setLoadingCitations(false);
        }
    }, []);

    useEffect(() => {
        fetchProjects();
    }, [fetchProjects]);

    useEffect(() => {
        fetchCitations(selectedProjectId);
    }, [fetchCitations, selectedProjectId]);

    const selectedProject = useMemo(
        () => projects.find((project) => project.id === selectedProjectId) ?? null,
        [projects, selectedProjectId]
    );

    const handleGenerate = async (event: React.FormEvent) => {
        event.preventDefault();
        if (!sourceUrl.trim()) return;

        setGenerating(true);
        setError(null);
        setSuccess(null);

        try {
            const response = await fetch(`${API}/generate`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ source: sourceUrl.trim(), format }),
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || "Failed to generate citation");
            }

            setGenerated(data);
            setManualCitation(data.citation_text);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Failed to generate citation");
        } finally {
            setGenerating(false);
        }
    };

    const handleSave = async () => {
        if (!selectedProjectId || !manualCitation.trim()) return;

        setSaving(true);
        setError(null);
        setSuccess(null);

        try {
            const response = await fetch(`${API}/citations`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    project_id: selectedProjectId,
                    citation_text: manualCitation.trim(),
                    csl_json: generated?.csl_json ?? {},
                }),
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || "Failed to save citation");
            }

            setSuccess("Citation saved to project bibliography.");
            setSourceUrl("");
            setGenerated(null);
            setManualCitation("");
            fetchCitations(selectedProjectId);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Failed to save citation");
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async (citationId: string) => {
        try {
            const response = await fetch(`${API}/citations/${citationId}`, {
                method: "DELETE",
            });
            if (!response.ok) throw new Error("Failed to delete citation");
            fetchCitations(selectedProjectId);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Failed to delete citation");
        }
    };

    const handleCreateProject = async () => {
        if (!newProjectTitle.trim()) return;

        setError(null);
        setSuccess(null);

        try {
            const response = await fetch(`${API}/projects`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    title: newProjectTitle.trim(),
                    description: "Created from citation manager",
                }),
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || "Failed to create project");
            }

            setNewProjectTitle("");
            setSuccess("Project created.");
            await fetchProjects();
            setSelectedProjectId(data.id);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Failed to create project");
        }
    };

    return (
        <div>
            <div className="page-header animate-in">
                <h1>Citation Manager</h1>
                <p>
                    Generate citations from URLs or DOIs, adjust the text, and keep a
                    project-level bibliography for research writing.
                </p>
            </div>

            {(error || success) && (
                <div className={`${styles.banner} ${error ? styles.errorBanner : styles.successBanner}`}>
                    <span>{error || success}</span>
                    <button
                        type="button"
                        className={styles.bannerClose}
                        onClick={() => {
                            setError(null);
                            setSuccess(null);
                        }}
                    >
                        ✕
                    </button>
                </div>
            )}

            <div className={styles.layout}>
                <aside className={`${styles.sidebar} card card-sm`}>
                    <div className={styles.panelHeader}>
                        <div>
                            <span className="section-label">Projects</span>
                            <h2 className={styles.panelTitle}>Bibliography Scope</h2>
                        </div>
                    </div>

                    <div className={styles.createProject}>
                        <input
                            className="input"
                            placeholder="New project title"
                            value={newProjectTitle}
                            onChange={(event) => setNewProjectTitle(event.target.value)}
                        />
                        <button type="button" className="btn btn-secondary" onClick={handleCreateProject}>
                            Create
                        </button>
                    </div>

                    {loadingProjects ? (
                        <p className={styles.muted}>Loading projects…</p>
                    ) : projects.length === 0 ? (
                        <p className={styles.muted}>Create a project to start saving citations.</p>
                    ) : (
                        <div className={styles.projectList}>
                            {projects.map((project) => (
                                <button
                                    key={project.id}
                                    type="button"
                                    className={`${styles.projectButton} ${selectedProjectId === project.id ? styles.projectButtonActive : ""}`}
                                    onClick={() => setSelectedProjectId(project.id)}
                                >
                                    <span className={styles.projectName}>{project.title}</span>
                                    <span className={styles.projectCount}>
                                        {selectedProjectId === project.id ? citations.length : ""}
                                    </span>
                                </button>
                            ))}
                        </div>
                    )}
                </aside>

                <div className={styles.content}>
                    <section className={`${styles.generatorCard} card animate-in`}>
                        <div className={styles.cardHeader}>
                            <div>
                                <span className="section-label">Generate</span>
                                <h2 className={styles.cardTitle}>URL or DOI to Citation</h2>
                            </div>
                            <div className={styles.formatRow}>
                                {FORMATS.map((item) => (
                                    <button
                                        key={item}
                                        type="button"
                                        className={`${styles.formatChip} ${format === item ? styles.formatChipActive : ""}`}
                                        onClick={() => setFormat(item)}
                                    >
                                        {item}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <form className={styles.generateForm} onSubmit={handleGenerate}>
                            <input
                                className="input"
                                placeholder="Paste a DOI or article URL"
                                value={sourceUrl}
                                onChange={(event) => setSourceUrl(event.target.value)}
                            />
                            <button type="submit" className="btn btn-primary" disabled={generating}>
                                {generating ? "Generating…" : "Generate"}
                            </button>
                        </form>

                        <div className={styles.helperText}>
                            Supports DOI input directly, DOI URLs, and basic webpage URLs.
                        </div>

                        <div className={styles.previewGrid}>
                            <div className={styles.previewPane}>
                                <span className="section-label">Citation Preview</span>
                                <textarea
                                    className={styles.textarea}
                                    value={manualCitation}
                                    onChange={(event) => setManualCitation(event.target.value)}
                                    placeholder="Generated citation text will appear here. You can edit it before saving."
                                />
                            </div>

                            <div className={styles.previewPane}>
                                <span className="section-label">Reference Details</span>
                                {generated ? (
                                    <div className={styles.metadataList}>
                                        <div>
                                            <strong>Title</strong>
                                            <p>{generated.metadata.title}</p>
                                        </div>
                                        <div>
                                            <strong>Authors</strong>
                                            <p>{generated.metadata.authors.join(", ") || "Not available"}</p>
                                        </div>
                                        <div>
                                            <strong>In-text</strong>
                                            <p>{generated.in_text_citation}</p>
                                        </div>
                                        <div>
                                            <strong>Source</strong>
                                            <p>{generated.metadata.url}</p>
                                        </div>
                                    </div>
                                ) : (
                                    <p className={styles.muted}>
                                        Generate a citation to see extracted metadata and an in-text citation hint.
                                    </p>
                                )}
                            </div>
                        </div>

                        <div className={styles.actions}>
                            <button
                                type="button"
                                className="btn btn-primary"
                                onClick={handleSave}
                                disabled={!selectedProjectId || !manualCitation.trim() || saving}
                            >
                                {saving ? "Saving…" : "Save to Project"}
                            </button>
                            {!selectedProject && (
                                <span className={styles.muted}>Select or create a project first.</span>
                            )}
                        </div>
                    </section>

                    <section className={`${styles.libraryCard} card animate-in`}>
                        <div className={styles.cardHeader}>
                            <div>
                                <span className="section-label">Saved References</span>
                                <h2 className={styles.cardTitle}>
                                    {selectedProject ? selectedProject.title : "Project bibliography"}
                                </h2>
                            </div>
                            <div className={styles.statPill}>
                                {loadingCitations ? "Loading…" : `${citations.length} items`}
                            </div>
                        </div>

                        {citations.length === 0 ? (
                            <div className={styles.emptyState}>
                                <div className={styles.emptyIcon}>📚</div>
                                <h3>No citations saved yet</h3>
                                <p>
                                    Generate one from a URL or DOI, review the text, then save it to the selected project.
                                </p>
                            </div>
                        ) : (
                            <div className={styles.citationList}>
                                {citations.map((citation, index) => (
                                    <article key={citation.id} className={styles.citationItem}>
                                        <div className={styles.citationIndex}>{index + 1}</div>
                                        <div className={styles.citationBody}>
                                            <p className={styles.citationText}>{citation.citation_text}</p>
                                            <span className={styles.citationMeta}>
                                                Added {new Date(citation.created_at).toLocaleDateString()}
                                            </span>
                                        </div>
                                        <button
                                            type="button"
                                            className="btn btn-ghost"
                                            onClick={() => handleDelete(citation.id)}
                                        >
                                            Delete
                                        </button>
                                    </article>
                                ))}
                            </div>
                        )}
                    </section>
                </div>
            </div>
        </div>
    );
}
