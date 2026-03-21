"use client";

import { useCallback, useEffect, useRef, useState, type RefObject } from "react";
import type { EditorView } from "@codemirror/view";
import { openSearchPanel } from "@codemirror/search";
import { insertEditorText } from "../editor/editorInsert";
import styles from "../editor-v2.module.css";

type EditorMenuBarProps = {
    editorView: EditorView | null;
    viewMode: "editor" | "split" | "preview";
    theme: "light" | "dark";
    onNewProject: () => void;
    onOpenTemplates: () => void;
    onExportZip: () => void;
    onRecompile: () => void;
    onSetViewMode: (m: "editor" | "split" | "preview") => void;
    onToggleTheme: () => void;
};

function useCloseOnOutsideClick(ref: RefObject<HTMLElement | null>, open: boolean, setOpen: (v: boolean) => void) {
    useEffect(() => {
        if (!open) return;
        const h = (e: MouseEvent) => {
            if (!ref.current) return;
            // Cross-origin iframes can surface Window proxies that throw on introspection.
            let target: EventTarget | null = null;
            try {
                target = e.target;
            } catch {
                setOpen(false);
                return;
            }
            try {
                if (!target) {
                    setOpen(false);
                    return;
                }
                const maybeNode = target as unknown as Node;
                if (typeof maybeNode.nodeType !== "number") {
                    setOpen(false);
                    return;
                }
                if (!ref.current.contains(maybeNode)) setOpen(false);
            } catch {
                setOpen(false);
            }
        };
        document.addEventListener("mousedown", h);
        return () => document.removeEventListener("mousedown", h);
    }, [open, ref, setOpen]);
}

function MenuDropdown({
    label,
    children,
}: {
    label: string;
    children: React.ReactNode;
}) {
    const [open, setOpen] = useState(false);
    const ref = useRef<HTMLDivElement>(null);
    useCloseOnOutsideClick(ref, open, setOpen);
    return (
        <div className={styles.menuDropdown} ref={ref}>
            <button type="button" className={styles.menuTrigger} onClick={() => setOpen((o) => !o)}>
                {label}
            </button>
            {open && <div className={styles.menuPanel}>{children}</div>}
        </div>
    );
}

export default function EditorMenuBar({
    editorView,
    viewMode,
    theme,
    onNewProject,
    onOpenTemplates,
    onExportZip,
    onRecompile,
    onSetViewMode,
    onToggleTheme,
}: EditorMenuBarProps) {
    const findPanel = useCallback(() => {
        if (editorView) openSearchPanel(editorView);
    }, [editorView]);

    const insert = useCallback(
        (text: string) => {
            insertEditorText(editorView, text);
        },
        [editorView]
    );

    return (
        <div className={styles.menuBar}>
            <MenuDropdown label="File">
                <button type="button" className={styles.menuItem} onClick={onNewProject}>
                    New project…
                </button>
                <button type="button" className={styles.menuItem} onClick={onOpenTemplates}>
                    New from template…
                </button>
                <button type="button" className={styles.menuItem} onClick={onExportZip}>
                    Download .zip
                </button>
            </MenuDropdown>
            <MenuDropdown label="Edit">
                <button type="button" className={styles.menuItem} onClick={findPanel}>
                    Find…
                </button>
                <button type="button" className={styles.menuItem} onClick={findPanel}>
                    Find & replace…
                </button>
            </MenuDropdown>
            <MenuDropdown label="Insert">
                <button type="button" className={styles.menuItem} onClick={() => insert("\\textbf{}")}>
                    Bold
                </button>
                <button type="button" className={styles.menuItem} onClick={() => insert("\\textit{}")}>
                    Italic
                </button>
                <button type="button" className={styles.menuItem} onClick={() => insert("$ $")}>
                    Math inline
                </button>
                <button type="button" className={styles.menuItem} onClick={() => insert("\\section{}\n")}>
                    Section
                </button>
                <button type="button" className={styles.menuItem} onClick={() => insert("\\subsection{}\n")}>
                    Subsection
                </button>
                <button type="button" className={styles.menuItem} onClick={() => insert("\\cite{}\n")}>
                    Citation
                </button>
            </MenuDropdown>
            <MenuDropdown label="View">
                <button
                    type="button"
                    className={styles.menuItem}
                    onClick={() => onSetViewMode("editor")}
                    disabled={viewMode === "editor"}
                >
                    Editor only
                </button>
                <button
                    type="button"
                    className={styles.menuItem}
                    onClick={() => onSetViewMode("split")}
                    disabled={viewMode === "split"}
                >
                    Split
                </button>
                <button
                    type="button"
                    className={styles.menuItem}
                    onClick={() => onSetViewMode("preview")}
                    disabled={viewMode === "preview"}
                >
                    Preview only
                </button>
                <button type="button" className={styles.menuItem} onClick={onToggleTheme}>
                    Theme: {theme === "dark" ? "Light" : "Dark"}
                </button>
            </MenuDropdown>
            <button type="button" className={styles.compileBtn} onClick={onRecompile}>
                Recompile
            </button>
        </div>
    );
}
