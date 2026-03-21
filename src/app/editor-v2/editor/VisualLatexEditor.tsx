"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { parseVisualDocument, serializeVisualDocument, type VisualBlock } from "./visualModel";
import styles from "../editor-v2.module.css";

type VisualLatexEditorProps = {
    value: string;
    onChange: (nextTex: string) => void;
};

export default function VisualLatexEditor({ value, onChange }: VisualLatexEditorProps) {
    const parsed = useMemo(() => parseVisualDocument(value), [value]);
    const [blocks, setBlocks] = useState<VisualBlock[]>(parsed.blocks);
    const [showRawBlocks, setShowRawBlocks] = useState(false);
    const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const idRef = useRef(0);
    const focusRef = useRef<HTMLElement | null>(null);

    useEffect(() => {
        const t = window.setTimeout(() => setBlocks(parsed.blocks), 0);
        return () => window.clearTimeout(t);
    }, [parsed.blocks]);

    useEffect(
        () => () => {
            if (timerRef.current) clearTimeout(timerRef.current);
        },
        []
    );

    const commit = (nextBlocks: VisualBlock[]) => {
        setBlocks(nextBlocks);
        if (timerRef.current) clearTimeout(timerRef.current);
        timerRef.current = setTimeout(() => {
            onChange(serializeVisualDocument({ ...parsed, blocks: nextBlocks }));
        }, 220);
    };

    const updateText = (id: string, text: string) => {
        commit(blocks.map((b) => (b.id === id ? { ...b, text } : b)));
    };

    const appendBlock = (kind: VisualBlock["kind"], text: string) => {
        idRef.current += 1;
        const next: VisualBlock = { id: `visual-${kind}-${idRef.current}`, kind, text };
        commit([...blocks, next]);
    };

    const applyCommand = (cmd: "bold" | "italic") => {
        if (!focusRef.current) return;
        focusRef.current.focus();
        document.execCommand(cmd);
    };

    const insertInlineToken = (token: string) => {
        if (!focusRef.current) return;
        focusRef.current.focus();
        document.execCommand("insertText", false, token);
    };

    const visibleBlocks = blocks.filter((b) => b.kind !== "raw");
    const rawBlocks = blocks.filter((b) => b.kind === "raw");

    return (
        <div className={styles.visualRoot}>
            <div className={styles.visualToolbar}>
                <div className={styles.visualToolbarTitleWrap}>
                    <span className={styles.visualToolbarTitle}>Visual Editor</span>
                    <span className={styles.visualToolbarMeta}>Document layout mode</span>
                </div>
                <div className={styles.visualToolbarActions}>
                    <button type="button" className={styles.visualToggleBtn} onClick={() => appendBlock("section", "New Section")}>
                        + Section
                    </button>
                    <button type="button" className={styles.visualToggleBtn} onClick={() => appendBlock("subsection", "New Subsection")}>
                        + Subsection
                    </button>
                    <button type="button" className={styles.visualToggleBtn} onClick={() => appendBlock("paragraph", "Write your paragraph here.")}>
                        + Paragraph
                    </button>
                    <button
                        type="button"
                        className={styles.visualToggleBtn}
                        onClick={() => setShowRawBlocks((v) => !v)}
                    >
                        {showRawBlocks ? "Hide raw LaTeX" : `Show raw LaTeX (${rawBlocks.length})`}
                    </button>
                </div>
            </div>
            <div className={styles.visualFormatRail}>
                <button type="button" className={styles.visualFormatBtn} onClick={() => applyCommand("bold")}>
                    B
                </button>
                <button type="button" className={styles.visualFormatBtn} onClick={() => applyCommand("italic")}>
                    I
                </button>
                <button type="button" className={styles.visualFormatBtn} onClick={() => insertInlineToken("$x^2$")}>
                    x^2
                </button>
                <button type="button" className={styles.visualFormatBtn} onClick={() => insertInlineToken("\\cite{}")}>
                    cite
                </button>
                <span className={styles.visualFormatSep} />
                <span className={styles.visualFormatHint}>Code tab keeps full LaTeX control</span>
            </div>
            <div className={styles.visualScroll}>
                <div className={styles.visualPage}>
                    <div className={styles.visualDocHeader}>
                        <span className={styles.visualDocPath}>main.tex</span>
                        <span className={styles.visualDocDivider}>/</span>
                        <span className={styles.visualDocSection}>Document</span>
                    </div>
                    {visibleBlocks.map((b) => (
                        <div key={b.id} className={styles.visualNode}>
                            {b.kind === "title" ? (
                                <h1
                                    className={`${styles.visualRichBlock} ${styles.visualRichTitle}`}
                                    contentEditable
                                    suppressContentEditableWarning
                                    onFocus={(e) => {
                                        focusRef.current = e.currentTarget;
                                    }}
                                    onInput={(e) => updateText(b.id, e.currentTarget.textContent ?? "")}
                                >
                                    {b.text}
                                </h1>
                            ) : b.kind === "authors" ? (
                                <p
                                    className={`${styles.visualRichBlock} ${styles.visualRichAuthors}`}
                                    contentEditable
                                    suppressContentEditableWarning
                                    onFocus={(e) => {
                                        focusRef.current = e.currentTarget;
                                    }}
                                    onInput={(e) => updateText(b.id, e.currentTarget.textContent ?? "")}
                                >
                                    {b.text}
                                </p>
                            ) : b.kind === "section" ? (
                                <h2
                                    className={`${styles.visualRichBlock} ${styles.visualRichSection}`}
                                    contentEditable
                                    suppressContentEditableWarning
                                    onFocus={(e) => {
                                        focusRef.current = e.currentTarget;
                                    }}
                                    onInput={(e) => updateText(b.id, e.currentTarget.textContent ?? "")}
                                >
                                    {b.text}
                                </h2>
                            ) : b.kind === "subsection" ? (
                                <h3
                                    className={`${styles.visualRichBlock} ${styles.visualRichSubsection}`}
                                    contentEditable
                                    suppressContentEditableWarning
                                    onFocus={(e) => {
                                        focusRef.current = e.currentTarget;
                                    }}
                                    onInput={(e) => updateText(b.id, e.currentTarget.textContent ?? "")}
                                >
                                    {b.text}
                                </h3>
                            ) : b.kind === "abstract" ? (
                                <>
                                    <div className={styles.visualAbstractHeading}>Abstract</div>
                                    <p
                                        className={`${styles.visualRichBlock} ${styles.visualRichParagraph}`}
                                        contentEditable
                                        suppressContentEditableWarning
                                        onFocus={(e) => {
                                            focusRef.current = e.currentTarget;
                                        }}
                                        onInput={(e) => updateText(b.id, e.currentTarget.textContent ?? "")}
                                    >
                                        {b.text}
                                    </p>
                                </>
                            ) : (
                                <p
                                    className={`${styles.visualRichBlock} ${styles.visualRichParagraph}`}
                                    contentEditable
                                    suppressContentEditableWarning
                                    onFocus={(e) => {
                                        focusRef.current = e.currentTarget;
                                    }}
                                    onInput={(e) => updateText(b.id, e.currentTarget.textContent ?? "")}
                                >
                                    {b.text}
                                </p>
                            )}
                        </div>
                    ))}
                    {showRawBlocks &&
                        rawBlocks.map((b) => (
                            <div key={b.id} className={styles.visualRawBlock}>
                                <div className={styles.visualLabel}>Raw LaTeX</div>
                                <textarea
                                    className={styles.visualTextarea}
                                    value={b.text}
                                    onChange={(e) => updateText(b.id, e.target.value)}
                                />
                            </div>
                        ))}
                </div>
            </div>
        </div>
    );
}
