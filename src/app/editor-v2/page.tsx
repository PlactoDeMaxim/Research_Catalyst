"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import WorkspaceShell from "./layout/WorkspaceShell";
import TemplatesModal, { type TemplateItem } from "./templates/TemplatesModal";
import { STORAGE_KEY, loadFromStorage, saveToStorage } from "./state/storage";
import type { ProjectState } from "./state/projectStore";

type ProjectMeta = {
    id: string;
    name: string;
    storageKey: string;
    createdAt: number;
    updatedAt: number;
};

const PROJECTS_INDEX_KEY = "research-catalyst:editor-v2:projects:index";

function createId(): string {
    return `p-${Math.random().toString(36).slice(2, 10)}-${Date.now().toString(36)}`;
}

function createStorageKey(projectId: string): string {
    return `research-catalyst:editor-v2:project:${projectId}`;
}

function buildInitialState(projectName: string, template?: TemplateItem): ProjectState {
    const mainId = `file-main-${Date.now()}`;
    const bibId = `file-bib-${Date.now()}`;
    return {
        projectName,
        files: [
            {
                id: mainId,
                path: "main.tex",
                name: "main.tex",
                kind: "tex",
                content:
                    template?.boilerplate ??
                    "\\documentclass[conference]{IEEEtran}\n\\title{Paper Title}\n\\author{Author Name}\n\\begin{document}\n\\maketitle\n\\begin{abstract}Write abstract.\\end{abstract}\n\\section{Introduction}\n\\end{document}\n",
                updatedAt: Date.now(),
            },
            {
                id: bibId,
                path: "bibliography.bib",
                name: "bibliography.bib",
                kind: "bib",
                content: "",
                updatedAt: Date.now(),
            },
        ],
        openTabIds: [mainId],
        activeTabId: mainId,
        mainFilePath: "main.tex",
        autoCompile: true,
        compileDelayMs: 1500,
        theme: "light",
        fontSize: 14,
        wordWrap: true,
    };
}

export default function EditorV2Page() {
    const [projects, setProjects] = useState<ProjectMeta[]>([]);
    const [activeProjectId, setActiveProjectId] = useState<string | null>(null);
    const [templatesOpen, setTemplatesOpen] = useState(false);
    const [createOpen, setCreateOpen] = useState(false);
    const [createName, setCreateName] = useState("");
    const [createError, setCreateError] = useState("");
    const [createTemplate, setCreateTemplate] = useState<TemplateItem | null>(null);

    useEffect(() => {
        const index = loadFromStorage<ProjectMeta[]>([], PROJECTS_INDEX_KEY);
        // One-time migration of old single-project storage.
        if (index.length === 0) {
            const legacy = loadFromStorage<ProjectState | null>(null as ProjectState | null, STORAGE_KEY);
            if (legacy && legacy.files?.length) {
                const id = createId();
                const meta: ProjectMeta = {
                    id,
                    name: legacy.projectName || "Migrated Project",
                    storageKey: createStorageKey(id),
                    createdAt: Date.now(),
                    updatedAt: Date.now(),
                };
                saveToStorage(legacy, meta.storageKey);
                saveToStorage([meta], PROJECTS_INDEX_KEY);
                const t = window.setTimeout(() => setProjects([meta]), 0);
                return () => window.clearTimeout(t);
            }
        }
        const ordered = index.sort((a, b) => b.updatedAt - a.updatedAt);
        const t = window.setTimeout(() => setProjects(ordered), 0);
        return () => window.clearTimeout(t);
    }, []);

    const persistProjects = useCallback((next: ProjectMeta[]) => {
        const ordered = [...next].sort((a, b) => b.updatedAt - a.updatedAt);
        setProjects(ordered);
        saveToStorage(ordered, PROJECTS_INDEX_KEY);
    }, []);

    const createProject = useCallback(
        (name: string, template?: TemplateItem) => {
            const projectName = name.trim();
            if (!projectName) return;
            const id = createId();
            const meta: ProjectMeta = {
                id,
                name: projectName,
                storageKey: createStorageKey(id),
                createdAt: Date.now(),
                updatedAt: Date.now(),
            };
            saveToStorage(buildInitialState(projectName, template), meta.storageKey);
            persistProjects([meta, ...projects]);
            setActiveProjectId(id);
            setCreateName("");
            setCreateError("");
            setCreateOpen(false);
            setCreateTemplate(null);
            setTemplatesOpen(false);
        },
        [persistProjects, projects]
    );

    const openCreateModal = useCallback((template?: TemplateItem) => {
        setCreateTemplate(template ?? null);
        setCreateName(template ? `${template.title} Project` : "");
        setCreateError("");
        setCreateOpen(true);
    }, []);

    const submitCreate = useCallback(() => {
        const trimmed = createName.trim();
        if (!trimmed) {
            setCreateError("Project name is required.");
            return;
        }
        createProject(trimmed, createTemplate ?? undefined);
    }, [createName, createProject, createTemplate]);

    const deleteProject = useCallback(
        (projectId: string) => {
            const project = projects.find((p) => p.id === projectId);
            if (!project) return;
            if (typeof window !== "undefined" && !window.confirm(`Delete "${project.name}"?`)) return;
            const next = projects.filter((p) => p.id !== projectId);
            persistProjects(next);
            if (typeof window !== "undefined") {
                try {
                    window.localStorage.removeItem(project.storageKey);
                } catch {
                    // ignore
                }
            }
            if (activeProjectId === projectId) setActiveProjectId(null);
        },
        [activeProjectId, persistProjects, projects]
    );

    const activeProject = useMemo(
        () => projects.find((p) => p.id === activeProjectId) ?? null,
        [projects, activeProjectId]
    );

    if (activeProject) {
        return (
            <WorkspaceShell
                key={activeProject.id}
                storageKey={activeProject.storageKey}
                onExitToProjects={() => setActiveProjectId(null)}
                onProjectPersist={(projectName) => {
                    persistProjects(
                        projects.map((p) =>
                            p.id === activeProject.id
                                ? { ...p, name: projectName || p.name, updatedAt: Date.now() }
                                : p
                        )
                    );
                }}
                onCreateProjectRequested={() => {
                    setActiveProjectId(null);
                    openCreateModal();
                }}
            />
        );
    }

    return (
        <div style={{ minHeight: "calc(100vh - 4rem)", background: "#f4f7fb", padding: "1.2rem" }}>
            <div
                style={{
                    maxWidth: "1100px",
                    margin: "0 auto",
                    background: "#fff",
                    border: "1px solid #dbe3ef",
                    borderRadius: "12px",
                    padding: "1rem",
                }}
            >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.9rem" }}>
                    <div>
                        <h2 style={{ margin: 0, fontSize: "1.1rem" }}>Paper Editor Projects</h2>
                        <p style={{ margin: "0.2rem 0 0", color: "#64748b", fontSize: "0.82rem" }}>
                            Open an existing project or create a new one.
                        </p>
                    </div>
                    <div style={{ display: "flex", gap: "0.45rem", alignItems: "center" }}>
                        <button
                            onClick={() => openCreateModal()}
                            style={{ border: "1px solid #15803d", background: "#16a34a", color: "#fff", borderRadius: "6px", padding: "0.35rem 0.6rem", fontSize: "0.8rem", fontWeight: 600 }}
                        >
                            New project
                        </button>
                        <button
                            onClick={() => setTemplatesOpen(true)}
                            style={{ border: "1px solid #d1d5db", background: "#fff", color: "#1f2937", borderRadius: "6px", padding: "0.35rem 0.6rem", fontSize: "0.8rem" }}
                        >
                            Browse templates
                        </button>
                    </div>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: "0.7rem" }}>
                    {projects.map((project) => (
                        <div key={project.id} style={{ border: "1px solid #d9e2ee", borderRadius: "10px", padding: "0.7rem", background: "#fcfdff" }}>
                            <div style={{ fontWeight: 700, fontSize: "0.86rem", color: "#0f172a", marginBottom: "0.2rem" }}>{project.name}</div>
                            <div style={{ fontSize: "0.72rem", color: "#64748b", marginBottom: "0.6rem" }}>
                                Updated {new Date(project.updatedAt).toLocaleString()}
                            </div>
                            <div style={{ display: "flex", gap: "0.4rem" }}>
                                <button
                                    onClick={() => setActiveProjectId(project.id)}
                                    style={{ border: "1px solid #0ea5e9", color: "#075985", background: "#e0f2fe", borderRadius: "6px", padding: "0.28rem 0.5rem", fontSize: "0.76rem", fontWeight: 600 }}
                                >
                                    Open
                                </button>
                                <button
                                    onClick={() => deleteProject(project.id)}
                                    style={{ border: "1px solid #fecaca", color: "#b91c1c", background: "#fff1f2", borderRadius: "6px", padding: "0.28rem 0.5rem", fontSize: "0.76rem" }}
                                >
                                    Delete
                                </button>
                            </div>
                        </div>
                    ))}
                    {projects.length === 0 ? (
                        <div style={{ gridColumn: "1 / -1", border: "1px dashed #cbd5e1", borderRadius: "10px", padding: "1rem", textAlign: "center", color: "#64748b", fontSize: "0.82rem" }}>
                            No projects yet. Create one or browse templates to start.
                        </div>
                    ) : null}
                </div>
            </div>
            <TemplatesModal
                open={templatesOpen}
                onClose={() => setTemplatesOpen(false)}
                onUseTemplate={(item) => {
                    setTemplatesOpen(false);
                    openCreateModal(item);
                }}
            />
            {createOpen ? (
                <div
                    onClick={() => setCreateOpen(false)}
                    style={{ position: "fixed", inset: 0, background: "rgba(15,23,42,0.38)", zIndex: 1400, display: "grid", placeItems: "center" }}
                >
                    <div
                        onClick={(e) => e.stopPropagation()}
                        style={{ width: "min(460px, 92vw)", background: "#fff", borderRadius: "12px", border: "1px solid #d9e2ee", padding: "0.95rem" }}
                    >
                        <div style={{ fontSize: "1rem", fontWeight: 700, marginBottom: "0.25rem" }}>Create Project</div>
                        <div style={{ fontSize: "0.78rem", color: "#64748b", marginBottom: "0.7rem" }}>
                            {createTemplate ? `Template: ${createTemplate.title}` : "Blank project"}
                        </div>
                        <label style={{ display: "block", fontSize: "0.76rem", color: "#334155", marginBottom: "0.25rem" }}>
                            Project name
                        </label>
                        <input
                            autoFocus
                            value={createName}
                            onChange={(e) => {
                                setCreateName(e.target.value);
                                if (createError) setCreateError("");
                            }}
                            onKeyDown={(e) => {
                                if (e.key === "Enter") submitCreate();
                            }}
                            placeholder="Enter a project name"
                            style={{ width: "100%", border: `1px solid ${createError ? "#ef4444" : "#d1d5db"}`, borderRadius: "7px", padding: "0.45rem 0.55rem", fontSize: "0.84rem" }}
                        />
                        {createError ? <div style={{ marginTop: "0.35rem", color: "#b91c1c", fontSize: "0.74rem" }}>{createError}</div> : null}
                        <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem", marginTop: "0.8rem" }}>
                            <button
                                onClick={() => setCreateOpen(false)}
                                style={{ border: "1px solid #d1d5db", background: "#fff", color: "#334155", borderRadius: "6px", padding: "0.3rem 0.55rem", fontSize: "0.78rem" }}
                            >
                                Cancel
                            </button>
                            <button
                                onClick={submitCreate}
                                style={{ border: "1px solid #15803d", background: "#16a34a", color: "#fff", borderRadius: "6px", padding: "0.3rem 0.58rem", fontSize: "0.78rem", fontWeight: 700 }}
                            >
                                Create project
                            </button>
                        </div>
                    </div>
                </div>
            ) : null}
        </div>
    );
}

