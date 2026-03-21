"use client";

import { useEffect, useMemo, useRef } from "react";
import CodeMirror, { type ViewUpdate } from "@uiw/react-codemirror";
import type { Diagnostic } from "@codemirror/lint";
import { EditorSelection } from "@codemirror/state";
import { EditorView } from "@codemirror/view";
import { buildBaseExtensions } from "./cmExtensions";

type LatexCodeEditorProps = {
    value: string;
    fontSize: number;
    wordWrap: boolean;
    diagnostics: Diagnostic[];
    jumpToLine?: number | null;
    onRecompile?: () => void;
    onEditorView?: (view: EditorView | null) => void;
    onChange: (next: string) => void;
};

export default function LatexCodeEditor({
    value,
    fontSize,
    wordWrap,
    diagnostics,
    jumpToLine,
    onRecompile,
    onEditorView,
    onChange,
}: LatexCodeEditorProps) {
    const viewRef = useRef<EditorView | null>(null);
    const lastJumpRef = useRef<number | null>(null);
    const extensions = useMemo(
        () => buildBaseExtensions(wordWrap, fontSize, diagnostics, onRecompile),
        [wordWrap, fontSize, diagnostics, onRecompile]
    );

    useEffect(() => {
        if (!jumpToLine || jumpToLine < 1) return;
        if (lastJumpRef.current === jumpToLine) return;
        const view = viewRef.current;
        if (!view) return;
        const targetLine = Math.min(jumpToLine, view.state.doc.lines);
        const pos = view.state.doc.line(targetLine).from;
        view.dispatch({
            selection: EditorSelection.cursor(pos),
            effects: EditorView.scrollIntoView(pos, { y: "center" }),
        });
        view.focus();
        lastJumpRef.current = jumpToLine;
    }, [jumpToLine]);

    useEffect(() => {
        lastJumpRef.current = null;
    }, [value]);

    useEffect(() => {
        return () => onEditorView?.(null);
    }, [onEditorView]);

    return (
        <CodeMirror
            value={value}
            height="100%"
            extensions={extensions}
            onChange={(next) => onChange(next)}
            onCreateEditor={(view) => {
                viewRef.current = view;
                onEditorView?.(view);
            }}
            onUpdate={(vu: ViewUpdate) => {
                if (vu.docChanged) return;
                if (!viewRef.current) {
                    viewRef.current = vu.view;
                }
            }}
            basicSetup={{
                lineNumbers: false,
                foldGutter: false,
                highlightActiveLine: true,
            }}
        />
    );
}

