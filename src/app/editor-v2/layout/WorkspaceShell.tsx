"use client";

import { useCallback, useMemo, useState } from "react";
import type { EditorView } from "@codemirror/view";
import type { Diagnostic } from "@codemirror/lint";
import styles from "../editor-v2.module.css";
import PaneResizer from "./PaneResizer";
import { inferMainFilePath, useProjectStore } from "../state/projectStore";
import FileTree from "../filetree/FileTree";
import EditorTabs from "../tabs/EditorTabs";
import LatexCodeEditor from "../editor/LatexCodeEditor";
import VisualLatexEditor from "../editor/VisualLatexEditor";
import { useCompileScheduler } from "../compile/compileScheduler";
import PdfPreviewPane from "../preview/PdfPreviewPane";
import EditorSettings from "../settings/EditorSettings";
import TemplatesModal, { type TemplateItem } from "../templates/TemplatesModal";
import OutlinePanel from "../outline/OutlinePanel";
import BibliographyPanel from "../bibliography/BibliographyPanel";
import CollabPanels from "../collab/CollabPanels";
import { compileDiagnosticsToLint } from "../editor/compileDiagnostics";
import EditorMenuBar from "./EditorMenuBar";

type ViewMode = "editor" | "split" | "preview";
type CenterMode = "code" | "visual";
type WorkspaceShellProps = {
    storageKey?: string;
    onExitToProjects?: () => void;
    onProjectPersist?: (projectName: string) => void;
    onCreateProjectRequested?: () => void;
};

function buildDiagnostics(source: string): Diagnostic[] {
    const diagnostics: Diagnostic[] = [];
    const lines = source.split(/\r?\n/);
    lines.forEach((line, idx) => {
        if (line.includes("TODO_ERROR")) {
            diagnostics.push({
                from: 0,
                to: Math.max(1, line.length),
                severity: "error",
                message: `Synthetic compile marker on line ${idx + 1}`,
                source: "paper-editor-v2",
            });
        }
    });
    return diagnostics;
}

export default function WorkspaceShell({
    storageKey,
    onExitToProjects,
    onProjectPersist,
    onCreateProjectRequested,
}: WorkspaceShellProps) {
    const store = useProjectStore({
        storageKey,
        onPersist: (next) => onProjectPersist?.(next.projectName),
    });
    const [leftWidth, setLeftWidth] = useState(260);
    const [rightWidthPct, setRightWidthPct] = useState(42);
    const [viewMode, setViewMode] = useState<ViewMode>("split");
    const [settingsOpen, setSettingsOpen] = useState(false);
    const [templatesOpen, setTemplatesOpen] = useState(false);
    const [collabOpen, setCollabOpen] = useState(false);
    const [jumpToLine, setJumpToLine] = useState<number | null>(null);
    const [editorView, setEditorView] = useState<EditorView | null>(null);
    const [centerMode, setCenterMode] = useState<CenterMode>("code");

    const activeFile = store.activeFile;
    const source = activeFile?.content ?? "";
    const projectFiles = store.state.files;
    const storedMainPath = store.state.mainFilePath;
    const inferredMainPath = useMemo(() => inferMainFilePath(projectFiles), [projectFiles]);
    const effectiveMainPath = useMemo(() => {
        if (storedMainPath && projectFiles.some((f) => f.path === storedMainPath)) {
            return storedMainPath;
        }
        return inferredMainPath;
    }, [projectFiles, storedMainPath, inferredMainPath]);

    const compile = useCompileScheduler({
        projectName: store.state.projectName,
        files: store.state.files,
        mainPath: effectiveMainPath,
        autoCompile: store.state.autoCompile,
        compileDelayMs: store.state.compileDelayMs,
    });

    const diagnostics = useMemo(() => {
        const base = buildDiagnostics(source);
        const fromCompile = compileDiagnosticsToLint(source, activeFile?.path, compile.diagnostics);
        return [...base, ...fromCompile];
    }, [source, activeFile?.path, compile.diagnostics]);

    const onInsertCitation = useCallback(
        (key: string) => {
            if (!store.state.activeTabId) return;
            const file = store.state.files.find((f) => f.id === store.state.activeTabId);
            if (!file || file.kind === "bib") return;
            store.updateFileContent(file.id, `${file.content}\n\\cite{${key}}\n`);
        },
        [store]
    );

    const onUseTemplate = useCallback(
        (item: TemplateItem) => {
            const main = store.state.files.find((f) => f.path.endsWith("main.tex"));
            if (main) {
                store.updateFileContent(main.id, item.boilerplate);
                store.openFile(main.id);
            } else {
                store.createFile("main.tex", item.boilerplate);
            }
            store.setProjectName(item.title);
            setTemplatesOpen(false);
        },
        [store]
    );

    const workspaceColumns = useMemo(() => {
        if (viewMode === "editor") return `${leftWidth}px 8px 1fr 0px 0px`;
        if (viewMode === "preview") return `${leftWidth}px 8px 0px 0px 1fr`;
        return `${leftWidth}px 8px 1fr 8px ${rightWidthPct}%`;
    }, [leftWidth, rightWidthPct, viewMode]);

    const activeKind = activeFile?.kind ?? "tex";
    const activeWordCount = useMemo(
        () => (source.trim() ? source.trim().split(/\s+/).length : 0),
        [source]
    );

    const mainTexForOutline = useMemo(() => {
        const f = projectFiles.find((x) => x.path === effectiveMainPath && x.kind === "tex");
        return f?.content ?? source;
    }, [projectFiles, effectiveMainPath, source]);

    return (
        <div className={`${styles.root} ${store.state.theme === "dark" ? styles.rootDark : ""}`}>
            <div className={styles.toolbar}>
                <div className={styles.toolbarGroup}>
                    {onExitToProjects ? (
                        <button className={styles.toolbarBtn} onClick={onExitToProjects}>
                            Projects
                        </button>
                    ) : null}
                    <EditorMenuBar
                        editorView={editorView}
                        viewMode={viewMode}
                        theme={store.state.theme}
                        onNewProject={() => {
                            if (onCreateProjectRequested) {
                                onCreateProjectRequested();
                                return;
                            }
                            if (typeof window !== "undefined" && window.confirm("Reset this project to a new blank paper?")) {
                                store.resetProject();
                            }
                        }}
                        onOpenTemplates={() => setTemplatesOpen(true)}
                        onExportZip={() => void store.exportProjectZip()}
                        onRecompile={() => void compile.runManualCompile()}
                        onSetViewMode={setViewMode}
                        onToggleTheme={() =>
                            store.setEditorPrefs(
                                store.state.fontSize,
                                store.state.wordWrap,
                                store.state.theme === "dark" ? "light" : "dark"
                            )
                        }
                    />
                    <label className={styles.toolbarMainLabel}>
                        Main
                        <select
                            className={styles.toolbarSelect}
                            title="Root .tex file for compilation"
                            value={store.state.mainFilePath ?? "__auto__"}
                            onChange={(e) => {
                                const v = e.target.value;
                                store.setMainFilePath(v === "__auto__" ? null : v);
                            }}
                        >
                            <option value="__auto__">Auto ({inferredMainPath})</option>
                            {store.state.files
                                .filter((f) => f.kind === "tex")
                                .map((f) => (
                                    <option key={f.id} value={f.path}>
                                        {f.path}
                                    </option>
                                ))}
                        </select>
                    </label>
                    <button className={styles.toolbarBtn} onClick={() => setSettingsOpen(true)}>
                        Settings
                    </button>
                </div>
                <div className={styles.projectName}>{store.state.projectName}</div>
                <div className={styles.toolbarGroup}>
                    <button className={styles.toolbarBtn} onClick={() => setCollabOpen((v) => !v)}>
                        Share
                    </button>
                    <button className={styles.toolbarBtn} onClick={() => void store.exportProjectZip()}>
                        Download .zip
                    </button>
                </div>
            </div>

            <div className={styles.workspace} style={{ gridTemplateColumns: workspaceColumns }}>
                <section className={`${styles.pane} ${styles.leftPane} ${styles.leftPaneStack}`}>
                    <div className={styles.fileTreeWrap}>
                        <FileTree
                            files={store.state.files}
                            activeFileId={store.state.activeTabId}
                            onOpenFile={store.openFile}
                            onRenameFile={store.renameFile}
                            onDeleteFile={store.deleteFile}
                            onDuplicateFile={store.duplicateFile}
                            onCreateFile={store.createFile}
                            onCreateFolder={store.createFolder}
                            onImportFiles={store.importFiles}
                        />
                    </div>
                    <div className={styles.outlineWrap}>
                        <OutlinePanel
                            latexSource={mainTexForOutline}
                            onJumpToLine={(line) => {
                                const mainF = store.state.files.find((f) => f.path === effectiveMainPath && f.kind === "tex");
                                if (!mainF) return;
                                store.openFile(mainF.id);
                                setViewMode("split");
                                setJumpToLine(null);
                                setTimeout(() => setJumpToLine(line), 0);
                            }}
                        />
                    </div>
                </section>
                <PaneResizer
                    axis="vertical"
                    onDelta={(delta) => setLeftWidth((w) => Math.max(180, Math.min(420, w + delta)))}
                />

                <section className={`${styles.pane} ${styles.centerPane} ${viewMode === "preview" ? styles.panelHidden : ""}`}>
                    <div className={styles.centerModeTabs}>
                        <button
                            className={`${styles.centerModeTab} ${centerMode === "code" ? styles.centerModeTabActive : ""}`}
                            onClick={() => setCenterMode("code")}
                        >
                            Code Editor
                        </button>
                        <button
                            className={`${styles.centerModeTab} ${centerMode === "visual" ? styles.centerModeTabActive : ""}`}
                            onClick={() => setCenterMode("visual")}
                        >
                            Visual Editor
                        </button>
                    </div>
                    <EditorTabs
                        files={store.state.files}
                        openTabIds={store.state.openTabIds}
                        activeTabId={store.state.activeTabId}
                        onActivateTab={store.openFile}
                        onCloseTab={store.closeTab}
                    />
                    <div
                        className={styles.editorBody}
                        style={{
                            gridTemplateRows:
                                activeKind === "bib" ? "minmax(0, 1fr) 260px" : "minmax(0, 1fr)",
                        }}
                    >
                        <div className={styles.editorMain}>
                            {centerMode === "code" ? (
                                <LatexCodeEditor
                                    value={source}
                                    fontSize={store.state.fontSize}
                                    wordWrap={store.state.wordWrap}
                                    diagnostics={diagnostics}
                                    jumpToLine={jumpToLine}
                                    onRecompile={() => void compile.runManualCompile()}
                                    onEditorView={setEditorView}
                                    onChange={(next) => {
                                        if (!activeFile) return;
                                        store.updateFileContent(activeFile.id, next);
                                    }}
                                />
                            ) : (
                                <VisualLatexEditor
                                    value={source}
                                    onChange={(next) => {
                                        if (!activeFile) return;
                                        store.updateFileContent(activeFile.id, next);
                                    }}
                                />
                            )}
                        </div>
                        {activeKind === "bib" && (
                            <BibliographyPanel
                                bibContent={source}
                                onChange={(next) => activeFile && store.updateFileContent(activeFile.id, next)}
                                onInsertCitation={onInsertCitation}
                            />
                        )}
                    </div>
                </section>

                <PaneResizer
                    axis="vertical"
                    onDelta={(delta) =>
                        setRightWidthPct((p) => Math.max(26, Math.min(64, p - (delta / 10))))
                    }
                />

                <section className={`${styles.pane} ${styles.rightPane} ${viewMode === "editor" ? styles.panelHidden : ""}`}>
                    <PdfPreviewPane
                        inlineUrl={compile.inlineUrl}
                        jobId={compile.jobId}
                        status={compile.status}
                        phase={compile.phase}
                        message={compile.message}
                        logs={compile.logs}
                        diagnostics={compile.diagnostics}
                        onRecompile={() => void compile.runManualCompile()}
                    />
                    {collabOpen && (
                        <CollabPanels
                            currentContent={source}
                            onRestoreVersion={(content) => activeFile && store.updateFileContent(activeFile.id, content)}
                        />
                    )}
                </section>
            </div>

            <div className={styles.statusBar}>
                <div className={styles.statusLeft}>
                    {activeFile?.path ?? "No file"} | {activeKind.toUpperCase()}
                </div>
                <div className={styles.statusCenter}>
                    Words: {activeWordCount} | Chars: {source.length}
                </div>
                <div className={styles.statusRight}>
                    Compile: {compile.phase} | Autosave: {store.saveStatus}
                </div>
            </div>

            <EditorSettings
                open={settingsOpen}
                fontSize={store.state.fontSize}
                wordWrap={store.state.wordWrap}
                autoCompile={store.state.autoCompile}
                compileDelayMs={store.state.compileDelayMs}
                theme={store.state.theme}
                onClose={() => setSettingsOpen(false)}
                onSave={(prefs) => {
                    store.setCompilePrefs(prefs.autoCompile, prefs.compileDelayMs);
                    store.setEditorPrefs(prefs.fontSize, prefs.wordWrap, prefs.theme);
                }}
            />
            <TemplatesModal open={templatesOpen} onClose={() => setTemplatesOpen(false)} onUseTemplate={onUseTemplate} />
        </div>
    );
}

