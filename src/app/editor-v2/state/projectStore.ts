"use client";

import { useCallback, useEffect, useLayoutEffect, useMemo, useState } from "react";
import JSZip from "jszip";
import { loadFromStorage, saveToStorage } from "./storage";

/** Pick the compiled entry: main.tex, else first file with \\documentclass, else first .tex. */
export function inferMainFilePath(files: ProjectFile[]): string {
    const texFiles = files.filter((f) => f.kind === "tex");
    const explicitMain = texFiles.find((f) => /(^|\/)main\.tex$/i.test(f.path));
    if (explicitMain) return explicitMain.path;
    const withDocument = texFiles.find((f) => /\\documentclass|\\begin\{document\}/.test(f.content));
    if (withDocument) return withDocument.path;
    return texFiles[0]?.path ?? "main.tex";
}

export type ProjectFile = {
    id: string;
    path: string;
    name: string;
    kind: "tex" | "bib" | "text" | "image" | "class" | "style" | "pdf" | "other";
    content: string;
    binaryBase64?: string;
    updatedAt: number;
};

export type ProjectState = {
    projectName: string;
    files: ProjectFile[];
    openTabIds: string[];
    activeTabId: string | null;
    /** User-selected root .tex; `null` = use auto-detection (inferMainFilePath). */
    mainFilePath: string | null;
    autoCompile: boolean;
    compileDelayMs: number;
    theme: "light" | "dark";
    fontSize: number;
    wordWrap: boolean;
};

const MAIN_SAMPLE = `\\documentclass[conference]{IEEEtran}
\\usepackage{amsmath,graphicx,cite}
\\title{My Research Paper}
\\author{Author Name}
\\begin{document}
\\maketitle
\\begin{abstract}
This is the abstract.
\\end{abstract}
\\section{Introduction}
Write your introduction here.
\\end{document}
`;

const BIB_SAMPLE = `@article{smith2023,
  author = {Smith, John},
  title = {Sample Reference},
  journal = {Journal of Examples},
  year = {2023}
}`;

function detectKind(fileName: string): ProjectFile["kind"] {
    const low = fileName.toLowerCase();
    if (low.endsWith(".tex")) return "tex";
    if (low.endsWith(".bib")) return "bib";
    if (low.endsWith(".cls")) return "class";
    if (low.endsWith(".sty")) return "style";
    if (low.endsWith(".pdf")) return "pdf";
    if (/\.(png|jpg|jpeg|gif|svg)$/i.test(low)) return "image";
    if (/\.(txt|md)$/i.test(low)) return "text";
    return "other";
}

function createId(): string {
    return `f-${Math.random().toString(36).slice(2, 10)}-${Date.now().toString(36)}`;
}

/** Stable IDs + timestamp so SSR and the client's first render match (hydration-safe). */
const DEFAULT_MAIN_ID = "file-default-main";
const DEFAULT_BIB_ID = "file-default-bib";
const DEFAULT_BOOT_TS = 0;

function createDefaultState(): ProjectState {
    return {
        projectName: "Untitled Project",
        files: [
            {
                id: DEFAULT_MAIN_ID,
                path: "main.tex",
                name: "main.tex",
                kind: "tex",
                content: MAIN_SAMPLE,
                updatedAt: DEFAULT_BOOT_TS,
            },
            {
                id: DEFAULT_BIB_ID,
                path: "bibliography.bib",
                name: "bibliography.bib",
                kind: "bib",
                content: BIB_SAMPLE,
                updatedAt: DEFAULT_BOOT_TS,
            },
        ],
        openTabIds: [DEFAULT_MAIN_ID],
        activeTabId: DEFAULT_MAIN_ID,
        mainFilePath: null,
        autoCompile: true,
        compileDelayMs: 1500,
        theme: "light",
        fontSize: 14,
        wordWrap: true,
    };
}

function mergeStoredProjectState(parsed: unknown): ProjectState {
    const d = createDefaultState();
    if (!parsed || typeof parsed !== "object") return d;
    const o = parsed as Partial<ProjectState>;
    return {
        ...d,
        ...o,
        mainFilePath: o.mainFilePath !== undefined ? o.mainFilePath : null,
        projectName: typeof o.projectName === "string" ? o.projectName : d.projectName,
        files: Array.isArray(o.files) ? o.files : d.files,
        openTabIds: Array.isArray(o.openTabIds) ? o.openTabIds : d.openTabIds,
        activeTabId: o.activeTabId !== undefined ? o.activeTabId : d.activeTabId,
        autoCompile: typeof o.autoCompile === "boolean" ? o.autoCompile : d.autoCompile,
        compileDelayMs: typeof o.compileDelayMs === "number" ? o.compileDelayMs : d.compileDelayMs,
        theme: o.theme === "dark" || o.theme === "light" ? o.theme : d.theme,
        fontSize: typeof o.fontSize === "number" ? o.fontSize : d.fontSize,
        wordWrap: typeof o.wordWrap === "boolean" ? o.wordWrap : d.wordWrap,
    };
}

async function fileToBase64(file: File): Promise<string> {
    const buffer = await file.arrayBuffer();
    const bytes = new Uint8Array(buffer);
    return bytesToBase64(bytes);
}

function bytesToBase64(bytes: Uint8Array): string {
    let binary = "";
    for (let i = 0; i < bytes.length; i += 1) {
        binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
}

export function useProjectStore(options?: {
    storageKey?: string;
    onPersist?: (next: ProjectState) => void;
}) {
    const storageKey = options?.storageKey;
    const onPersist = options?.onPersist;
    // Never read localStorage in useState: server HTML must match the client's first paint.
    const [state, setState] = useState<ProjectState>(() => createDefaultState());
    const [hydrated, setHydrated] = useState(false);
    const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "saved">("saved");

    useLayoutEffect(() => {
        const loaded = loadFromStorage(createDefaultState(), storageKey);
        queueMicrotask(() => {
            setState(mergeStoredProjectState(loaded));
            setHydrated(true);
        });
    }, [storageKey]);

    useEffect(() => {
        if (!hydrated) return;
        const saveMark = setTimeout(() => setSaveStatus("saving"), 0);
        const timer = setTimeout(() => {
            saveToStorage(state, storageKey);
            onPersist?.(state);
            setSaveStatus("saved");
        }, 250);
        return () => {
            clearTimeout(saveMark);
            clearTimeout(timer);
        };
    }, [state, hydrated, storageKey, onPersist]);

    const activeFile = useMemo(
        () => state.files.find((f) => f.id === state.activeTabId) ?? null,
        [state.activeTabId, state.files]
    );

    const updateFileContent = useCallback((fileId: string, next: string) => {
        setState((prev) => ({
            ...prev,
            files: prev.files.map((f) =>
                f.id === fileId
                    ? {
                          ...f,
                          content: next,
                          updatedAt: Date.now(),
                      }
                    : f
            ),
        }));
    }, []);

    const openFile = useCallback((fileId: string) => {
        setState((prev) => ({
            ...prev,
            activeTabId: fileId,
            openTabIds: prev.openTabIds.includes(fileId) ? prev.openTabIds : [...prev.openTabIds, fileId],
        }));
    }, []);

    const closeTab = useCallback((fileId: string) => {
        setState((prev) => {
            const openTabIds = prev.openTabIds.filter((id) => id !== fileId);
            const nextActive =
                prev.activeTabId === fileId
                    ? openTabIds[openTabIds.length - 1] ?? null
                    : prev.activeTabId;
            return {
                ...prev,
                openTabIds,
                activeTabId: nextActive,
            };
        });
    }, []);

    const renameFile = useCallback((fileId: string, nextName: string) => {
        const normalized = nextName.trim();
        if (!normalized) return;
        setState((prev) => ({
            ...prev,
            files: prev.files.map((file) => {
                if (file.id !== fileId) return file;
                const segments = file.path.split("/");
                segments[segments.length - 1] = normalized;
                return {
                    ...file,
                    name: normalized,
                    path: segments.join("/"),
                    kind: detectKind(normalized),
                    updatedAt: Date.now(),
                };
            }),
        }));
    }, []);

    const createFile = useCallback((path: string, content = "") => {
        const trimmed = path.trim();
        if (!trimmed) return;
        const name = trimmed.split("/").pop() || trimmed;
        const id = createId();
        setState((prev) => ({
            ...prev,
            files: [
                ...prev.files,
                {
                    id,
                    path: trimmed,
                    name,
                    kind: detectKind(name),
                    content,
                    updatedAt: Date.now(),
                },
            ],
            openTabIds: [...prev.openTabIds, id],
            activeTabId: id,
        }));
    }, []);

    const deleteFile = useCallback((fileId: string) => {
        setState((prev) => {
            const files = prev.files.filter((f) => f.id !== fileId);
            const openTabIds = prev.openTabIds.filter((id) => id !== fileId);
            const activeTabId = prev.activeTabId === fileId ? openTabIds[openTabIds.length - 1] ?? null : prev.activeTabId;
            return { ...prev, files, openTabIds, activeTabId };
        });
    }, []);

    const duplicateFile = useCallback((fileId: string) => {
        setState((prev) => {
            const source = prev.files.find((f) => f.id === fileId);
            if (!source) return prev;
            const extIndex = source.name.lastIndexOf(".");
            const base = extIndex >= 0 ? source.name.slice(0, extIndex) : source.name;
            const ext = extIndex >= 0 ? source.name.slice(extIndex) : "";
            const name = `${base}-copy${ext}`;
            const pathSegments = source.path.split("/");
            pathSegments[pathSegments.length - 1] = name;
            const copy: ProjectFile = {
                ...source,
                id: createId(),
                name,
                path: pathSegments.join("/"),
                updatedAt: Date.now(),
            };
            return {
                ...prev,
                files: [...prev.files, copy],
                openTabIds: [...prev.openTabIds, copy.id],
                activeTabId: copy.id,
            };
        });
    }, []);

    const importFiles = useCallback(async (fileList: FileList) => {
        const entries = Array.from(fileList);
        const newFiles: ProjectFile[] = [];
        for (const file of entries) {
            const kind = detectKind(file.name);
            if (file.name.toLowerCase().endsWith(".zip")) {
                const zip = await JSZip.loadAsync(await file.arrayBuffer());
                const names = Object.keys(zip.files).filter((n) => !zip.files[n].dir);
                for (const entryPath of names) {
                    const zipEntry = zip.files[entryPath];
                    const name = entryPath.split("/").pop() || entryPath;
                    const entryKind = detectKind(name);
                    if (entryKind === "image" || entryKind === "pdf" || entryKind === "other") {
                        const bytes = await zipEntry.async("uint8array");
                        newFiles.push({
                            id: createId(),
                            path: entryPath,
                            name,
                            kind: entryKind,
                            content: "",
                            binaryBase64: bytesToBase64(bytes),
                            updatedAt: Date.now(),
                        });
                        continue;
                    }
                    const content = await zipEntry.async("string");
                    newFiles.push({
                        id: createId(),
                        path: entryPath,
                        name,
                        kind: entryKind,
                        content,
                        updatedAt: Date.now(),
                    });
                }
                continue;
            }
            if (kind === "image" || kind === "pdf") {
                const b64 = await fileToBase64(file);
                newFiles.push({
                    id: createId(),
                    path: file.name,
                    name: file.name,
                    kind,
                    content: "",
                    binaryBase64: b64,
                    updatedAt: Date.now(),
                });
            } else {
                const text = await file.text();
                newFiles.push({
                    id: createId(),
                    path: file.name,
                    name: file.name,
                    kind,
                    content: text,
                    updatedAt: Date.now(),
                });
            }
        }
        setState((prev) => ({
            ...prev,
            files: [
                ...prev.files.filter((existing) => !newFiles.some((added) => added.path === existing.path)),
                ...newFiles,
            ],
        }));
    }, []);

    const setProjectName = useCallback((name: string) => {
        setState((prev) => ({ ...prev, projectName: name }));
    }, []);

    const setCompilePrefs = useCallback((autoCompile: boolean, compileDelayMs: number) => {
        setState((prev) => ({ ...prev, autoCompile, compileDelayMs }));
    }, []);

    const setEditorPrefs = useCallback((fontSize: number, wordWrap: boolean, theme: "light" | "dark") => {
        setState((prev) => ({ ...prev, fontSize, wordWrap, theme }));
    }, []);

    const setMainFilePath = useCallback((path: string | null) => {
        setState((prev) => ({ ...prev, mainFilePath: path }));
    }, []);

    const createFolder = useCallback((folderPath: string) => {
        const normalized = folderPath.replace(/\\/g, "/").replace(/\/+$/, "").trim();
        if (!normalized) return;
        const keepPath = `${normalized}/.gitkeep`;
        setState((prev) => {
            if (prev.files.some((f) => f.path === keepPath)) {
                return prev;
            }
            const id = createId();
            return {
                ...prev,
                files: [
                    ...prev.files,
                    {
                        id,
                        path: keepPath,
                        name: ".gitkeep",
                        kind: "text" as const,
                        content: "",
                        updatedAt: Date.now(),
                    },
                ],
            };
        });
    }, []);

    const resetProject = useCallback(() => {
        setState(createDefaultState());
    }, []);

    const exportProjectZip = useCallback(async () => {
        const zip = new JSZip();
        for (const f of state.files) {
            const rel = f.path.replace(/\\/g, "/");
            if (f.binaryBase64) {
                try {
                    const binary = Uint8Array.from(atob(f.binaryBase64), (c) => c.charCodeAt(0));
                    zip.file(rel, binary);
                } catch {
                    zip.file(rel, f.content);
                }
            } else {
                zip.file(rel, f.content);
            }
        }
        const blob = await zip.generateAsync({ type: "blob" });
        const safe = state.projectName.replace(/[^\w\-]+/g, "_").slice(0, 80) || "project";
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `${safe}.zip`;
        a.click();
        URL.revokeObjectURL(a.href);
    }, [state.files, state.projectName]);

    return {
        state,
        saveStatus,
        activeFile,
        updateFileContent,
        openFile,
        closeTab,
        renameFile,
        createFile,
        createFolder,
        deleteFile,
        duplicateFile,
        importFiles,
        setProjectName,
        setCompilePrefs,
        setEditorPrefs,
        setMainFilePath,
        resetProject,
        exportProjectZip,
    };
}

