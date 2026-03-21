import { EditorView, keymap, lineNumbers, placeholder } from "@codemirror/view";
import { Compartment, EditorState, Prec } from "@codemirror/state";
import { defaultKeymap, history, historyKeymap, indentWithTab } from "@codemirror/commands";
import { searchKeymap } from "@codemirror/search";
import {
    bracketMatching,
    foldGutter,
    foldKeymap,
    indentOnInput,
    syntaxHighlighting,
    defaultHighlightStyle,
    StreamLanguage,
} from "@codemirror/language";
import { closeBrackets, closeBracketsKeymap, autocompletion } from "@codemirror/autocomplete";
import { lintGutter, Diagnostic, linter } from "@codemirror/lint";
import { stex } from "@codemirror/legacy-modes/mode/stex";

export const wrapCompartment = new Compartment();
export const fontSizeCompartment = new Compartment();

const latexLanguage = StreamLanguage.define(stex);

export function buildBaseExtensions(
    wordWrap: boolean,
    fontSizePx: number,
    diagnostics: Diagnostic[],
    onRecompile?: () => void
) {
    const recompileKeymap =
        onRecompile &&
        Prec.highest(
            keymap.of([
                {
                    key: "Mod-Enter",
                    run: () => {
                        onRecompile();
                        return true;
                    },
                },
            ])
        );

    return [
        lineNumbers(),
        foldGutter(),
        latexLanguage,
        bracketMatching(),
        closeBrackets(),
        history(),
        autocompletion(),
        lintGutter(),
        indentOnInput(),
        syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
        EditorState.tabSize.of(4),
        placeholder("Start writing your LaTeX..."),
        ...(recompileKeymap ? [recompileKeymap] : []),
        keymap.of([
            indentWithTab,
            ...defaultKeymap,
            ...historyKeymap,
            ...searchKeymap,
            ...foldKeymap,
            ...closeBracketsKeymap,
        ]),
        wrapCompartment.of(wordWrap ? EditorView.lineWrapping : []),
        fontSizeCompartment.of(
            EditorView.theme({
                ".cm-content, .cm-gutter": {
                    fontSize: `${fontSizePx}px`,
                    fontFamily: "var(--font-mono)",
                },
            })
        ),
        EditorView.theme({
            "&": { height: "100%", minHeight: 0 },
            ".cm-editor": { height: "100%", minHeight: 0 },
            ".cm-scroller": {
                height: "100%",
                minHeight: 0,
                overflowY: "scroll",
                overflowX: "auto",
                overscrollBehavior: "contain",
            },
            ".cm-gutters": { height: "100%", minHeight: 0 },
        }),
        linter(() => diagnostics),
        EditorState.allowMultipleSelections.of(true),
        EditorState.readOnly.of(false),
        EditorView.contentAttributes.of({ spellcheck: "false" }),
        EditorState.languageData.of(() => [{ autocomplete: [] }]),
        EditorState.phrases.of({}),
    ];
}

