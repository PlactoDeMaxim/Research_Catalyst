"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { ProjectFile } from "../state/projectStore";
import styles from "../editor-v2.module.css";

type FileTreeProps = {
    files: ProjectFile[];
    activeFileId: string | null;
    onOpenFile: (id: string) => void;
    onRenameFile: (id: string, nextName: string) => void;
    onDeleteFile: (id: string) => void;
    onDuplicateFile: (id: string) => void;
    onCreateFile: (path: string) => void;
    onCreateFolder: (folderPath: string) => void;
    onImportFiles: (files: FileList) => Promise<void>;
};

const iconForKind: Record<ProjectFile["kind"], string> = {
    tex: "TeX",
    bib: "Bib",
    text: "Txt",
    image: "Img",
    class: "Cls",
    style: "Sty",
    pdf: "PDF",
    other: "File",
};

export default function FileTree({
    files,
    activeFileId,
    onOpenFile,
    onRenameFile,
    onDeleteFile,
    onDuplicateFile,
    onCreateFile,
    onCreateFolder,
    onImportFiles,
}: FileTreeProps) {
    const inputRef = useRef<HTMLInputElement | null>(null);
    const sorted = useMemo(
        () => [...files].sort((a, b) => a.path.localeCompare(b.path)),
        [files]
    );

    const [menu, setMenu] = useState<{ x: number; y: number; fileId: string } | null>(null);

    useEffect(() => {
        if (!menu) return;
        const close = () => setMenu(null);
        const t = window.setTimeout(() => document.addEventListener("click", close), 0);
        return () => {
            window.clearTimeout(t);
            document.removeEventListener("click", close);
        };
    }, [menu]);

    return (
        <div style={{ height: "100%", display: "flex", flexDirection: "column", background: "#fff" }}>
            <div className={styles.fileTreeTop}>
                <div className={styles.fileTreeTitle}>File tree</div>
                <div className={styles.fileTreeActions}>
                    <button
                        className={styles.fileTreeActionBtn}
                        onClick={() => onCreateFile(prompt("New file path", "sections/new-section.tex") || "")}
                    >
                        New File
                    </button>
                    <button
                        className={styles.fileTreeActionBtn}
                        onClick={() => {
                            const folder = prompt("New folder path", "sections");
                            if (folder) onCreateFolder(folder);
                        }}
                    >
                        New Folder
                    </button>
                    <button className={styles.fileTreeActionBtn} onClick={() => inputRef.current?.click()}>
                        Upload
                    </button>
                    <input
                        ref={inputRef}
                        type="file"
                        multiple
                        style={{ display: "none" }}
                        onChange={(e) => {
                            const selected = e.target.files;
                            if (selected && selected.length > 0) {
                                void onImportFiles(selected);
                            }
                            e.currentTarget.value = "";
                        }}
                    />
                </div>
                <div className={styles.fileTreeMeta}>{files.length} files</div>
            </div>
            <div className={styles.fileTreeList}>
                {sorted.map((file) => {
                    const isActive = file.id === activeFileId;
                    const depth = Math.max(0, file.path.split("/").length - 1);
                    return (
                        <div
                            key={file.id}
                            className={`${styles.fileTreeRow} ${isActive ? styles.fileTreeRowActive : ""}`}
                            style={{ marginLeft: `${depth * 12}px` }}
                            onClick={() => onOpenFile(file.id)}
                            onDoubleClick={() => {
                                const next = prompt("Rename file", file.name);
                                if (next) onRenameFile(file.id, next);
                            }}
                            onContextMenu={(e) => {
                                e.preventDefault();
                                setMenu({ x: e.clientX, y: e.clientY, fileId: file.id });
                            }}
                        >
                            <span className={styles.fileTypeBadge}>{iconForKind[file.kind]}</span>
                            <span className={styles.fileTreePath}>{file.path}</span>
                            <button
                                className={styles.fileTreeIconBtn}
                                onClick={(e) => {
                                    e.stopPropagation();
                                    onDuplicateFile(file.id);
                                }}
                            >
                                ⧉
                            </button>
                            <button
                                className={styles.fileTreeIconBtn}
                                style={{ color: "#ef4444" }}
                                onClick={(e) => {
                                    e.stopPropagation();
                                    if (confirm(`Delete ${file.name}?`)) onDeleteFile(file.id);
                                }}
                            >
                                ✕
                            </button>
                        </div>
                    );
                })}
            </div>
            {menu && (
                <div
                    role="presentation"
                    onClick={(e) => e.stopPropagation()}
                    style={{
                        position: "fixed",
                        left: menu.x,
                        top: menu.y,
                        zIndex: 300,
                        background: "#ffffff",
                        border: "1px solid #e5e7eb",
                        borderRadius: "8px",
                        minWidth: "160px",
                        padding: "0.25rem 0",
                        boxShadow: "0 8px 24px rgba(0,0,0,0.3)",
                    }}
                    onMouseLeave={() => setMenu(null)}
                >
                    <button
                        type="button"
                        style={{
                            display: "block",
                            width: "100%",
                            textAlign: "left",
                            padding: "0.4rem 0.75rem",
                            background: "transparent",
                            border: "none",
                            color: "#1f2937",
                            fontSize: "0.8rem",
                            cursor: "pointer",
                        }}
                        onClick={() => {
                            const file = files.find((f) => f.id === menu.fileId);
                            if (file) {
                                const next = prompt("Rename", file.name);
                                if (next) onRenameFile(file.id, next);
                            }
                            setMenu(null);
                        }}
                    >
                        Rename…
                    </button>
                    <button
                        type="button"
                        style={{
                            display: "block",
                            width: "100%",
                            textAlign: "left",
                            padding: "0.4rem 0.75rem",
                            background: "transparent",
                            border: "none",
                            color: "#1f2937",
                            fontSize: "0.8rem",
                            cursor: "pointer",
                        }}
                        onClick={() => {
                            onDuplicateFile(menu.fileId);
                            setMenu(null);
                        }}
                    >
                        Duplicate
                    </button>
                    <button
                        type="button"
                        style={{
                            display: "block",
                            width: "100%",
                            textAlign: "left",
                            padding: "0.4rem 0.75rem",
                            background: "transparent",
                            border: "none",
                            color: "#fca5a5",
                            fontSize: "0.8rem",
                            cursor: "pointer",
                        }}
                        onClick={() => {
                            const file = files.find((f) => f.id === menu.fileId);
                            if (file && confirm(`Delete ${file.name}?`)) onDeleteFile(file.id);
                            setMenu(null);
                        }}
                    >
                        Delete
                    </button>
                </div>
            )}
        </div>
    );
}
