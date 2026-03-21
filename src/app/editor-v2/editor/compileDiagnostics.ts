import type { Diagnostic } from "@codemirror/lint";

export type CompileDiag = {
    file?: string;
    line?: number;
    message?: string;
    severity?: string;
};

function lineToOffset(source: string, line: number): number {
    const lines = source.split(/\r?\n/);
    const L = Math.min(Math.max(1, line), Math.max(1, lines.length));
    let off = 0;
    for (let i = 0; i < L - 1; i++) {
        off += (lines[i]?.length ?? 0) + 1;
    }
    return off;
}

function basename(p: string): string {
    const n = p.replace(/\\/g, "/").split("/").pop();
    return n || p;
}

/** Map backend log diagnostics to CodeMirror lint entries for the active source file. */
export function compileDiagnosticsToLint(
    source: string,
    activePath: string | undefined,
    raw: CompileDiag[] | undefined
): Diagnostic[] {
    if (!activePath || !raw?.length) return [];
    const activeBase = basename(activePath);
    const out: Diagnostic[] = [];
    for (const d of raw) {
        const line = d.line;
        if (line == null || line < 1) continue;
        const f = d.file?.trim();
        if (f) {
            const fb = basename(f);
            const isSandboxCopy = fb === "compiled_input.tex" || fb === "compiled_input.log";
            if (
                !isSandboxCopy &&
                fb !== activeBase &&
                !activePath.replace(/\\/g, "/").endsWith(f.replace(/\\/g, "/"))
            ) {
                continue;
            }
        }
        const from = lineToOffset(source, line);
        const lineText = source.split(/\r?\n/)[line - 1] ?? "";
        const to = from + Math.max(1, lineText.length);
        const sev = d.severity === "warning" ? "warning" : "error";
        out.push({
            from,
            to,
            severity: sev,
            message: d.message ?? "LaTeX error",
            source: "latex-compile",
        });
    }
    return out;
}
