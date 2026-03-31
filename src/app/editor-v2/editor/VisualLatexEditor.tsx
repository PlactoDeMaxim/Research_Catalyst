"use client";

import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { parseVisualDocument, serializeVisualDocument, type VisualBlock } from "./visualModel";
import styles from "../editor-v2.module.css";

type VisualLatexEditorProps = {
    value: string;
    onChange: (nextTex: string) => void;
};

/**
 * contentEditable + React children {text} re-renders reset the DOM every keystroke, which
 * causes caret jumps and "backwards" typing. We keep text in refs and only push to the DOM
 * when the block is not focused or when the source changes from outside (e.g. Code tab).
 */
function RichBlock({
    block,
    className,
    tag: Tag,
    onUpdate,
    onRegisterFocus,
}: {
    block: VisualBlock;
    className: string;
    tag: "h1" | "h2" | "h3" | "p";
    onUpdate: (id: string, text: string) => void;
    onRegisterFocus: (el: HTMLElement | null) => void;
}) {
    const elRef = useRef<HTMLElement | null>(null);

    useLayoutEffect(() => {
        const el = elRef.current;
        if (!el) return;
        if (document.activeElement === el) return;
        const next = block.text;
        if (el.textContent !== next) {
            el.textContent = next;
        }
    }, [block.text, block.id]);

    return (
        <Tag
            ref={elRef as React.RefObject<HTMLHeadingElement & HTMLParagraphElement>}
            className={className}
            contentEditable
            suppressContentEditableWarning
            dir="ltr"
            spellCheck
            onFocus={(e) => {
                onRegisterFocus(e.currentTarget);
            }}
            onBlur={() => {
                onRegisterFocus(null);
            }}
            onInput={(e) => onUpdate(block.id, e.currentTarget.textContent ?? "")}
        />
    );
}

export default function VisualLatexEditor({ value, onChange }: VisualLatexEditorProps) {
    const parsed = useMemo(() => parseVisualDocument(value), [value]);
    const [blocks, setBlocks] = useState<VisualBlock[]>(() => parsed.blocks);
    const [showRawBlocks, setShowRawBlocks] = useState(false);
    const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const idRef = useRef(0);
    const focusRef = useRef<HTMLElement | null>(null);
    /** Last full TeX emitted from this editor — skip re-parsing our own round-trips. */
    const lastEmittedTexRef = useRef<string | null>(null);
    /** TeX we last applied into `blocks` from props (external / initial). */
    const lastSyncedValueRef = useRef<string>(value);

    useEffect(
        () => () => {
            if (timerRef.current) clearTimeout(timerRef.current);
        },
        []
    );

    // Only replace blocks when `value` changed from outside (Code tab, template, file switch),
    // not on every visual edit (which would fight contentEditable and scramble caret / order).
    useEffect(() => {
        if (value === lastEmittedTexRef.current) {
            return;
        }
        if (value === lastSyncedValueRef.current) {
            return;
        }
        lastSyncedValueRef.current = value;
        lastEmittedTexRef.current = null;
        setBlocks(parseVisualDocument(value).blocks);
    }, [value]);

    const commit = useCallback(
        (nextBlocks: VisualBlock[]) => {
            setBlocks(nextBlocks);
            if (timerRef.current) clearTimeout(timerRef.current);
            timerRef.current = setTimeout(() => {
                const doc = { ...parsed, blocks: nextBlocks };
                const tex = serializeVisualDocument(doc);
                lastEmittedTexRef.current = tex;
                lastSyncedValueRef.current = tex;
                onChange(tex);
            }, 220);
        },
        [onChange, parsed]
    );

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
        <div className={styles.visualRoot} dir="ltr">
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
                <div className={styles.visualPage} dir="ltr">
                    <div className={styles.visualDocHeader}>
                        <span className={styles.visualDocPath}>main.tex</span>
                        <span className={styles.visualDocDivider}>/</span>
                        <span className={styles.visualDocSection}>Document</span>
                    </div>
                    {visibleBlocks.map((b) => (
                        <div key={b.id} className={styles.visualNode}>
                            {b.kind === "title" ? (
                                <RichBlock
                                    block={b}
                                    tag="h1"
                                    className={`${styles.visualRichBlock} ${styles.visualRichTitle}`}
                                    onUpdate={updateText}
                                    onRegisterFocus={(el) => {
                                        focusRef.current = el;
                                    }}
                                />
                            ) : b.kind === "authors" ? (
                                <RichBlock
                                    block={b}
                                    tag="p"
                                    className={`${styles.visualRichBlock} ${styles.visualRichAuthors}`}
                                    onUpdate={updateText}
                                    onRegisterFocus={(el) => {
                                        focusRef.current = el;
                                    }}
                                />
                            ) : b.kind === "section" ? (
                                <RichBlock
                                    block={b}
                                    tag="h2"
                                    className={`${styles.visualRichBlock} ${styles.visualRichSection}`}
                                    onUpdate={updateText}
                                    onRegisterFocus={(el) => {
                                        focusRef.current = el;
                                    }}
                                />
                            ) : b.kind === "subsection" ? (
                                <RichBlock
                                    block={b}
                                    tag="h3"
                                    className={`${styles.visualRichBlock} ${styles.visualRichSubsection}`}
                                    onUpdate={updateText}
                                    onRegisterFocus={(el) => {
                                        focusRef.current = el;
                                    }}
                                />
                            ) : b.kind === "abstract" ? (
                                <>
                                    <div className={styles.visualAbstractHeading}>Abstract</div>
                                    <RichBlock
                                        block={b}
                                        tag="p"
                                        className={`${styles.visualRichBlock} ${styles.visualRichParagraph}`}
                                        onUpdate={updateText}
                                        onRegisterFocus={(el) => {
                                            focusRef.current = el;
                                        }}
                                    />
                                </>
                            ) : (
                                <RichBlock
                                    block={b}
                                    tag="p"
                                    className={`${styles.visualRichBlock} ${styles.visualRichParagraph}`}
                                    onUpdate={updateText}
                                    onRegisterFocus={(el) => {
                                        focusRef.current = el;
                                    }}
                                />
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
