"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import WorkspaceShell from "./layout/WorkspaceShell";
import TemplatesModal, { type TemplateItem } from "./templates/TemplatesModal";
import { STORAGE_KEY, loadFromStorage, saveToStorage } from "./state/storage";
import type { ProjectState } from "./state/projectStore";
import {
    createServerEditorProject,
    deleteServerEditorProject,
    getServerEditorProject,
    listServerEditorProjects,
    type ServerEditorProject,
    updateServerEditorProject,
} from "./state/serverProjects";

type ProjectMeta = {
    id: string;
    name: string;
    storageKey: string;
    createdAt: number;
    updatedAt: number;
};

const PROJECTS_INDEX_KEY = "research-catalyst:editor-v2:projects:index";

function toProjectMeta(project: ServerEditorProject): ProjectMeta {
    return {
        id: project.id,
        name: project.title,
        storageKey: project.storage_key || createStorageKey(project.id),
        createdAt: project.created_at ? new Date(project.created_at).getTime() : Date.now(),
        updatedAt: project.updated_at ? new Date(project.updated_at).getTime() : Date.now(),
    };
}

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
    const [serverBacked, setServerBacked] = useState(false);
    const [templatesOpen, setTemplatesOpen] = useState(false);
    const [createOpen, setCreateOpen] = useState(false);
    const [createName, setCreateName] = useState("");
    const [createError, setCreateError] = useState("");
    const [createTemplate, setCreateTemplate] = useState<TemplateItem | null>(null);

    useEffect(() => {
        let cancelled = false;

        const loadProjects = async () => {
            try {
                const remote = await listServerEditorProjects();
                if (cancelled) return;
                setServerBacked(true);
                if (remote.length > 0) {
                    const ordered = remote.map(toProjectMeta).sort((a, b) => b.updatedAt - a.updatedAt);
                    setProjects(ordered);
                    saveToStorage(ordered, PROJECTS_INDEX_KEY);
                    return;
                }

                const index = loadFromStorage<ProjectMeta[]>([], PROJECTS_INDEX_KEY);
                const legacy = loadFromStorage<ProjectState | null>(null as ProjectState | null, STORAGE_KEY);
                const migrated: ProjectMeta[] = [];

                if (legacy && legacy.files?.length) {
                    const legacyStorageKey = createStorageKey(createId());
                    const created = await createServerEditorProject({
                        title: legacy.projectName || "Migrated Project",
                        storage_key: legacyStorageKey,
                        state: legacy,
                    });
                    saveToStorage(legacy, legacyStorageKey);
                    migrated.push(toProjectMeta(created));
                } else {
                    for (const project of index) {
                        const state = loadFromStorage<ProjectState | null>(null as ProjectState | null, project.storageKey);
                        if (!state?.files?.length) continue;
                        const created = await createServerEditorProject({
                            title: state.projectName || project.name,
                            storage_key: project.storageKey,
                            state,
                        });
                        saveToStorage(state, project.storageKey);
                        migrated.push(toProjectMeta(created));
                    }
                }

                if (cancelled) return;
                const ordered = migrated.sort((a, b) => b.updatedAt - a.updatedAt);
                setProjects(ordered);
                saveToStorage(ordered, PROJECTS_INDEX_KEY);
            } catch {
                setServerBacked(false);
                const index = loadFromStorage<ProjectMeta[]>([], PROJECTS_INDEX_KEY);
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
                        setProjects([meta]);
                        return;
                    }
                }
                setProjects(index.sort((a, b) => b.updatedAt - a.updatedAt));
            }
        };

        void loadProjects();
        return () => {
            cancelled = true;
        };
    }, []);

    const persistProjects = useCallback((next: ProjectMeta[]) => {
        const ordered = [...next].sort((a, b) => b.updatedAt - a.updatedAt);
        setProjects(ordered);
        saveToStorage(ordered, PROJECTS_INDEX_KEY);
    }, []);

    const createProject = useCallback(
        async (name: string, template?: TemplateItem) => {
            const projectName = name.trim();
            if (!projectName) return;
            const state = buildInitialState(projectName, template);
            const id = createId();
            const storageKey = createStorageKey(id);
            let meta: ProjectMeta = {
                id,
                name: projectName,
                storageKey,
                createdAt: Date.now(),
                updatedAt: Date.now(),
            };
            if (serverBacked) {
                try {
                    const created = await createServerEditorProject({
                        title: projectName,
                        storage_key: storageKey,
                        state,
                    });
                    meta = toProjectMeta(created);
                } catch {
                    // Fall back to local-only if server sync is unavailable.
                }
            }
            saveToStorage(state, meta.storageKey);
            persistProjects([meta, ...projects]);
            setActiveProjectId(meta.id);
            setCreateName("");
            setCreateError("");
            setCreateOpen(false);
            setCreateTemplate(null);
            setTemplatesOpen(false);
        },
        [persistProjects, projects, serverBacked]
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
        void createProject(trimmed, createTemplate ?? undefined);
    }, [createName, createProject, createTemplate]);

    const deleteProject = useCallback(
        async (projectId: string) => {
            const project = projects.find((p) => p.id === projectId);
            if (!project) return;
            if (typeof window !== "undefined" && !window.confirm(`Delete "${project.name}"?`)) return;
            if (serverBacked) {
                try {
                    await deleteServerEditorProject(projectId);
                } catch {
                    // local deletion still proceeds so the UI does not get stuck
                }
            }
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
        [activeProjectId, persistProjects, projects, serverBacked]
    );

    const openProject = useCallback(
        async (project: ProjectMeta) => {
            if (serverBacked) {
                try {
                    const remote = await getServerEditorProject(project.id);
                    if (remote?.editor_state) {
                        saveToStorage(remote.editor_state, project.storageKey);
                    }
                } catch {
                    // Local cache remains the fallback.
                }
            }
            setActiveProjectId(project.id);
        },
        [serverBacked]
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
                onProjectPersist={(nextState) => {
                    saveToStorage(nextState, activeProject.storageKey);
                    if (serverBacked) {
                        void updateServerEditorProject(activeProject.id, {
                            title: nextState.projectName,
                            storage_key: activeProject.storageKey,
                            state: nextState,
                        });
                    }
                    persistProjects(
                        projects.map((p) =>
                            p.id === activeProject.id
                                ? { ...p, name: nextState.projectName || p.name, updatedAt: Date.now() }
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
                                    onClick={() => void openProject(project)}
                                    style={{ border: "1px solid #0ea5e9", color: "#075985", background: "#e0f2fe", borderRadius: "6px", padding: "0.28rem 0.5rem", fontSize: "0.76rem", fontWeight: 600 }}
                                >
                                    Open
                                </button>
                                <button
                                    onClick={() => void deleteProject(project.id)}
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

