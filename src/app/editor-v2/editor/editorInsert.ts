import type { EditorView } from "@codemirror/view";

export function insertEditorText(view: EditorView | null, text: string) {
    if (!view) return;
    const { from, to } = view.state.selection.main;
    view.dispatch({ changes: { from, to, insert: text } });
    view.focus();
}
