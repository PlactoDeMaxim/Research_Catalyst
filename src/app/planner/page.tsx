"use client";

import { useState, useEffect, useCallback } from "react";
import styles from "./page.module.css";

const API = "http://localhost:8000/api/planner";

/* ── Types ── */
interface Milestone {
    id: string;
    title: string;
    description: string;
    due_date: string;
    completed: boolean;
    phase: string;
    order: number;
}
interface Phase {
    title: string;
    description: string;
    order: number;
    milestones: Milestone[];
}
interface Project {
    id: string;
    title: string;
    topic: string;
    domain: string;
    deadline: string;
    created_at: string;
    phases: Phase[];
    milestones: Milestone[];
}

/* ── Inline Edit Component ── */
function EditableField({
    value, onSave, tag = "span", className, type = "text",
}: {
    value: string; onSave: (v: string) => void; tag?: "span" | "h4" | "p"; className?: string; type?: string;
}) {
    const [editing, setEditing] = useState(false);
    const [draft, setDraft] = useState(value);

    useEffect(() => setDraft(value), [value]);

    if (!editing) {
        const props = { className: `${className || ""} ${styles.editable}`, onClick: () => setEditing(true), title: "Click to edit" };
        if (tag === "h4") return <h4 {...props}>{value || "(empty)"}</h4>;
        if (tag === "p") return <p {...props}>{value || "(empty)"}</p>;
        return <span {...props}>{value || "(empty)"}</span>;
    }

    return (
        <input
            className={`input ${styles.inlineInput}`}
            type={type}
            value={draft}
            autoFocus
            onChange={(e) => setDraft(e.target.value)}
            onBlur={() => { onSave(draft); setEditing(false); }}
            onKeyDown={(e) => { if (e.key === "Enter") { onSave(draft); setEditing(false); } if (e.key === "Escape") setEditing(false); }}
        />
    );
}

/* ── Main Page ── */
export default function PlannerPage() {
    const [projects, setProjects] = useState<Project[]>([]);
    const [activeId, setActiveId] = useState<string | null>(null);
    const [activeProject, setActiveProject] = useState<Project | null>(null);

    // Create project state
    const [showCreate, setShowCreate] = useState(false);
    const [newTitle, setNewTitle] = useState("");
    const [newTopic, setNewTopic] = useState("");
    const [newDomain, setNewDomain] = useState("general");
    const [customDomain, setCustomDomain] = useState("");
    const [newDeadline, setNewDeadline] = useState("");

    // Loading
    const [loading, setLoading] = useState(false);
    const [generating, setGenerating] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Add milestone state
    const [addingPhase, setAddingPhase] = useState<string | null>(null);
    const [addTitle, setAddTitle] = useState("");
    const [addDesc, setAddDesc] = useState("");
    const [addDate, setAddDate] = useState("");

    /* ── Fetch projects ── */
    const fetchProjects = useCallback(async () => {
        try {
            const r = await fetch(`${API}/projects`);
            const data = await r.json();
            setProjects(data.projects || []);
        } catch { /* ignore */ }
    }, []);

    /* ── Fetch single project ── */
    const fetchProject = useCallback(async (id: string) => {
        try {
            const r = await fetch(`${API}/projects/${id}`);
            if (!r.ok) return;
            const data = await r.json();
            setActiveProject(data);
        } catch { /* ignore */ }
    }, []);

    useEffect(() => { fetchProjects(); }, [fetchProjects]);
    useEffect(() => { if (activeId) fetchProject(activeId); }, [activeId, fetchProject]);

    /* ── Create project ── */
    const handleCreate = async () => {
        if (!newTitle.trim()) return;
        setLoading(true);
        try {
            const r = await fetch(`${API}/projects`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ title: newTitle, topic: newTopic, domain: newDomain === "other" ? customDomain : newDomain, deadline: newDeadline }),
            });
            const proj = await r.json();
            await fetchProjects();
            setActiveId(proj.id);
            setShowCreate(false);
            setNewTitle(""); setNewTopic(""); setNewDomain("general"); setNewDeadline(""); setCustomDomain("");
        } catch { setError("Failed to create project"); }
        finally { setLoading(false); }
    };

    /* ── Delete project ── */
    const handleDeleteProject = async (id: string) => {
        await fetch(`${API}/projects/${id}`, { method: "DELETE" });
        if (activeId === id) { setActiveId(null); setActiveProject(null); }
        fetchProjects();
    };

    /* ── Generate plan ── */
    const handleGenerate = async () => {
        if (!activeProject) return;
        setGenerating(true);
        setError(null);
        try {
            const r = await fetch(`${API}/projects/${activeProject.id}/generate`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    topic: activeProject.topic,
                    domain: activeProject.domain,
                    deadline: activeProject.deadline,
                }),
            });
            if (!r.ok) throw new Error("Generation failed");
            const data = await r.json();
            setActiveProject(data);
            fetchProjects();
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Plan generation failed");
        } finally {
            setGenerating(false);
        }
    };

    /* ── Toggle milestone completion ── */
    const toggleMilestone = async (mid: string, completed: boolean) => {
        if (!activeProject) return;
        await fetch(`${API}/projects/${activeProject.id}/milestones/${mid}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ completed: !completed }),
        });
        fetchProject(activeProject.id);
    };

    /* ── Update milestone field ── */
    const updateField = async (mid: string, field: string, value: string) => {
        if (!activeProject) return;
        await fetch(`${API}/projects/${activeProject.id}/milestones/${mid}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ [field]: value }),
        });
        fetchProject(activeProject.id);
    };

    /* ── Delete milestone ── */
    const deleteMilestone = async (mid: string) => {
        if (!activeProject) return;
        await fetch(`${API}/projects/${activeProject.id}/milestones/${mid}`, { method: "DELETE" });
        fetchProject(activeProject.id);
    };

    /* ── Add milestone ── */
    const handleAddMilestone = async (phase: string) => {
        if (!activeProject || !addTitle.trim()) return;
        await fetch(`${API}/projects/${activeProject.id}/milestones`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ title: addTitle, description: addDesc, due_date: addDate, phase }),
        });
        setAddingPhase(null); setAddTitle(""); setAddDesc(""); setAddDate("");
        fetchProject(activeProject.id);
    };

    /* ── Progress calc ── */
    const milestones = activeProject?.milestones || [];
    const completed = milestones.filter((m) => m.completed).length;
    const progress = milestones.length > 0 ? Math.round((completed / milestones.length) * 100) : 0;

    return (
        <div>
            <div className="page-header animate-in">
                <h1>Research Planner</h1>
                <p>Create projects, generate research plans, track milestones, and manage your entire research lifecycle.</p>
            </div>

            {error && (
                <div className={styles.errorBanner}>
                    ⚠️ {error}
                    <button className={styles.errorClose} onClick={() => setError(null)}>✕</button>
                </div>
            )}

            <div className={styles.plannerLayout}>
                {/* ── LEFT: Project List ── */}
                <div className={`card ${styles.projectPanel} animate-in`}>
                    <div className={styles.projectPanelHeader}>
                        <h3 className={styles.panelTitle}>Projects</h3>
                        <button className="btn btn-ghost" onClick={() => setShowCreate(!showCreate)} style={{ fontSize: "1.1rem", padding: "2px 6px" }}>+</button>
                    </div>

                    {showCreate && (
                        <div className={styles.createForm}>
                            <input className="input" placeholder="Project Title" value={newTitle} onChange={(e) => setNewTitle(e.target.value)} />
                            <input className="input" placeholder="Research Topic" value={newTopic} onChange={(e) => setNewTopic(e.target.value)} />
                            <select className="input" value={newDomain} onChange={(e) => setNewDomain(e.target.value)}>
                                <optgroup label="General">
                                    <option value="general">General Research</option>
                                </optgroup>
                                <optgroup label="Computer Science">
                                    <option value="machine_learning">Machine Learning</option>
                                    <option value="deep_learning">Deep Learning</option>
                                    <option value="nlp">Natural Language Processing</option>
                                    <option value="computer_vision">Computer Vision</option>
                                    <option value="data_science">Data Science</option>
                                    <option value="cybersecurity">Cybersecurity</option>
                                    <option value="software_engineering">Software Engineering</option>
                                    <option value="robotics">Robotics &amp; Automation</option>
                                </optgroup>
                                <optgroup label="Engineering">
                                    <option value="electrical_engineering">Electrical Engineering</option>
                                    <option value="mechanical_engineering">Mechanical Engineering</option>
                                    <option value="biomedical_engineering">Biomedical Engineering</option>
                                </optgroup>
                                <optgroup label="Sciences">
                                    <option value="biology">Biology</option>
                                    <option value="physics">Physics</option>
                                    <option value="chemistry">Chemistry</option>
                                    <option value="mathematics">Mathematics</option>
                                </optgroup>
                                <optgroup label="Custom">
                                    <option value="other">Other (type your own)</option>
                                </optgroup>
                            </select>
                            {newDomain === "other" && (
                                <input className="input" placeholder="Enter your domain…" value={customDomain} onChange={(e) => setCustomDomain(e.target.value)} />
                            )}
                            <input className="input" type="date" value={newDeadline} onChange={(e) => setNewDeadline(e.target.value)} />
                            <button className="btn btn-primary" onClick={handleCreate} disabled={loading} style={{ width: "100%" }}>
                                {loading ? "Creating…" : "Create Project"}
                            </button>
                        </div>
                    )}

                    <div className={styles.projectList}>
                        {projects.length === 0 && !showCreate && (
                            <p className={styles.emptyText}>No projects yet. Click + to create one.</p>
                        )}
                        {projects.map((p) => (
                            <div
                                key={p.id}
                                className={`${styles.projectItem} ${activeId === p.id ? styles.projectActive : ""}`}
                                onClick={() => setActiveId(p.id)}
                            >
                                <div className={styles.projectItemInfo}>
                                    <span className={styles.projectItemTitle}>{p.title}</span>
                                    <span className={styles.projectItemMeta}>
                                        {p.milestones.length} milestones · {p.domain}
                                    </span>
                                </div>
                                <button
                                    className={styles.deleteBtn}
                                    onClick={(e) => { e.stopPropagation(); handleDeleteProject(p.id); }}
                                    title="Delete project"
                                >🗑</button>
                            </div>
                        ))}
                    </div>
                </div>

                {/* ── RIGHT: Project Detail ── */}
                <div className={styles.detailPanel}>
                    {!activeProject ? (
                        <div className={`card ${styles.emptyState} animate-in`}>
                            <span className={styles.emptyIcon}>📋</span>
                            <h3>Select or create a project</h3>
                            <p>Choose a project from the left panel to view its research plan, or create a new one.</p>
                        </div>
                    ) : (
                        <>
                            {/* ── Project Header + Progress ── */}
                            <div className={`card ${styles.progressCard} animate-in`}>
                                <div className={styles.progressHeader}>
                                    <div>
                                        <h2 className={styles.projectTitle}>{activeProject.title}</h2>
                                        <p className={styles.progressMeta}>
                                            {activeProject.topic && <><strong>Topic:</strong> {activeProject.topic} · </>}
                                            <strong>Domain:</strong> {activeProject.domain}
                                            {activeProject.deadline && <> · <strong>Deadline:</strong> {new Date(activeProject.deadline).toLocaleDateString()}</>}
                                        </p>
                                        <p className={styles.progressMeta}>
                                            {completed} of {milestones.length} milestones completed
                                        </p>
                                    </div>
                                    <div className={styles.progressPercent}>{progress}%</div>
                                </div>
                                <div className={styles.progressBarTrack}>
                                    <div className={styles.progressBarFill} style={{ width: `${progress}%` }} />
                                </div>

                                {/* Generate / Regenerate plan */}
                                {milestones.length === 0 ? (
                                    <button className="btn btn-primary" onClick={handleGenerate} disabled={generating} style={{ marginTop: "var(--space-sm)" }}>
                                        {generating ? "Generating plan…" : "⚡ Generate Research Plan"}
                                    </button>
                                ) : (
                                    <button className="btn btn-ghost" onClick={handleGenerate} disabled={generating} style={{ marginTop: "var(--space-sm)", fontSize: "0.82rem" }}>
                                        {generating ? "Regenerating…" : "🔄 Regenerate Plan"}
                                    </button>
                                )}
                            </div>

                            {/* ── Phases + Milestones ── */}
                            {activeProject.phases.map((phase) => {
                                const phaseMilestones = milestones.filter((m) => m.phase === phase.title);
                                const phaseComplete = phaseMilestones.filter((m) => m.completed).length;
                                const phaseProgress = phaseMilestones.length > 0 ? Math.round((phaseComplete / phaseMilestones.length) * 100) : 0;

                                return (
                                    <div key={phase.title} className={`${styles.phaseSection} animate-in`}>
                                        <div className={styles.phaseHeader}>
                                            <div>
                                                <h3 className={styles.phaseTitle}>
                                                    <span className={styles.phaseOrder}>Phase {phase.order + 1}</span>
                                                    {phase.title}
                                                </h3>
                                                <p className={styles.phaseDesc}>{phase.description}</p>
                                            </div>
                                            <span className={styles.phaseProg}>{phaseProgress}%</span>
                                        </div>
                                        <div className={styles.phaseProgressTrack}>
                                            <div className={styles.phaseProgressFill} style={{ width: `${phaseProgress}%` }} />
                                        </div>

                                        <div className={styles.milestoneList}>
                                            {phaseMilestones.map((m, mIdx) => (
                                                <div key={m.id} className={`${styles.milestoneCard} ${m.completed ? styles.milestoneCompleted : ""}`}>
                                                    <div className={styles.milestoneLeft}>
                                                        <button
                                                            className={`${styles.checkbox} ${m.completed ? styles.checked : ""}`}
                                                            onClick={() => toggleMilestone(m.id, m.completed)}
                                                        >
                                                            {m.completed ? "✓" : ""}
                                                        </button>
                                                        <span className={styles.milestoneNum}>{mIdx + 1}</span>
                                                    </div>
                                                    <div className={styles.milestoneContent}>
                                                        <EditableField
                                                            value={m.title}
                                                            onSave={(v) => updateField(m.id, "title", v)}
                                                            tag="h4"
                                                            className={styles.milestoneTitle}
                                                        />
                                                        <EditableField
                                                            value={m.description}
                                                            onSave={(v) => updateField(m.id, "description", v)}
                                                            tag="p"
                                                            className={styles.milestoneDesc}
                                                        />
                                                    </div>
                                                    <div className={styles.milestoneRight}>
                                                        <EditableField
                                                            value={m.due_date}
                                                            onSave={(v) => updateField(m.id, "due_date", v)}
                                                            className={styles.milestoneDate}
                                                            type="date"
                                                        />
                                                        <button className={styles.deleteBtn} onClick={() => deleteMilestone(m.id)} title="Delete milestone">🗑</button>
                                                    </div>
                                                </div>
                                            ))}

                                            {/* Add milestone inline */}
                                            {addingPhase === phase.title ? (
                                                <div className={styles.addMilestoneForm}>
                                                    <input className="input" placeholder="Milestone title" value={addTitle} onChange={(e) => setAddTitle(e.target.value)} autoFocus />
                                                    <input className="input" placeholder="Description" value={addDesc} onChange={(e) => setAddDesc(e.target.value)} />
                                                    <input className="input" type="date" value={addDate} onChange={(e) => setAddDate(e.target.value)} />
                                                    <div className={styles.addFormBtns}>
                                                        <button className="btn btn-primary" onClick={() => handleAddMilestone(phase.title)} style={{ fontSize: "0.8rem" }}>Add</button>
                                                        <button className="btn btn-ghost" onClick={() => setAddingPhase(null)} style={{ fontSize: "0.8rem" }}>Cancel</button>
                                                    </div>
                                                </div>
                                            ) : (
                                                <button className={styles.addMilestoneBtn} onClick={() => setAddingPhase(phase.title)}>
                                                    + Add Milestone
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                );
                            })}

                            {milestones.length === 0 && (
                                <div className={`card ${styles.emptyState} animate-in`}>
                                    <span className={styles.emptyIcon}>⚡</span>
                                    <h3>No plan yet</h3>
                                    <p>Click &quot;Generate Research Plan&quot; above to create phases and milestones automatically.</p>
                                </div>
                            )}
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}
