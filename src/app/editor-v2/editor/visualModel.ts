export type VisualBlock =
    | { id: string; kind: "title"; text: string }
    | { id: string; kind: "authors"; text: string }
    | { id: string; kind: "abstract"; text: string }
    | { id: string; kind: "section"; text: string }
    | { id: string; kind: "subsection"; text: string }
    | { id: string; kind: "paragraph"; text: string }
    | { id: string; kind: "raw"; text: string };

export type VisualDocument = {
    preamble: string;
    footer: string;
    blocks: VisualBlock[];
};

function createId(prefix: string, i: number) {
    return `${prefix}-${i}`;
}

function upsertCommand(preamble: string, cmd: "title" | "author", value: string): string {
    const re = new RegExp(String.raw`\\${cmd}\{[^}]*\}`);
    const next = `\\${cmd}{${value}}`;
    if (re.test(preamble)) return preamble.replace(re, next);
    return `${preamble.trimEnd()}\n${next}\n`;
}

export function parseVisualDocument(tex: string): VisualDocument {
    const beginMarker = "\\begin{document}";
    const endMarker = "\\end{document}";
    const beginIdx = tex.indexOf(beginMarker);
    const endIdx = tex.lastIndexOf(endMarker);

    const preamble =
        beginIdx >= 0 ? tex.slice(0, beginIdx + beginMarker.length) : "\\documentclass{article}\n\\begin{document}";
    const body =
        beginIdx >= 0 && endIdx > beginIdx
            ? tex.slice(beginIdx + beginMarker.length, endIdx)
            : beginIdx >= 0
              ? tex.slice(beginIdx + beginMarker.length)
              : tex;
    const footer = endIdx >= 0 ? tex.slice(endIdx) : "\n\\end{document}\n";

    const blocks: VisualBlock[] = [];
    const titleMatch = preamble.match(/\\title\{([^}]*)\}/);
    if (titleMatch) blocks.push({ id: createId("title", 0), kind: "title", text: titleMatch[1] });
    const authorMatch = preamble.match(/\\author\{([^}]*)\}/);
    if (authorMatch) blocks.push({ id: createId("authors", 0), kind: "authors", text: authorMatch[1] });

    const abstractRe = /\\begin\{abstract\}([\s\S]*?)\\end\{abstract\}/m;
    const abstractMatch = body.match(abstractRe);
    let restBody = body;
    if (abstractMatch) {
        blocks.push({ id: createId("abstract", 0), kind: "abstract", text: abstractMatch[1].trim() });
        restBody = body.replace(abstractRe, "\n");
    }

    const lines = restBody.split(/\r?\n/);
    let paraBuf: string[] = [];
    let rawBuf: string[] = [];
    let idx = 0;
    const flushPara = () => {
        const t = paraBuf.join(" ").trim();
        if (t) blocks.push({ id: createId("p", idx++), kind: "paragraph", text: t });
        paraBuf = [];
    };
    const flushRaw = () => {
        const t = rawBuf.join("\n").trim();
        if (t) blocks.push({ id: createId("raw", idx++), kind: "raw", text: t });
        rawBuf = [];
    };

    for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) {
            flushPara();
            flushRaw();
            continue;
        }
        const sec = trimmed.match(/^\\section\*?\{(.+)\}$/);
        if (sec) {
            flushPara();
            flushRaw();
            blocks.push({ id: createId("sec", idx++), kind: "section", text: sec[1] });
            continue;
        }
        const sub = trimmed.match(/^\\subsection\*?\{(.+)\}$/);
        if (sub) {
            flushPara();
            flushRaw();
            blocks.push({ id: createId("sub", idx++), kind: "subsection", text: sub[1] });
            continue;
        }
        if (trimmed.startsWith("\\")) {
            flushPara();
            rawBuf.push(line);
            continue;
        }
        if (rawBuf.length > 0) flushRaw();
        paraBuf.push(line);
    }
    flushPara();
    flushRaw();

    return { preamble, footer, blocks };
}

export function serializeVisualDocument(doc: VisualDocument): string {
    const titleBlock = doc.blocks.find((b) => b.kind === "title");
    const authorBlock = doc.blocks.find((b) => b.kind === "authors");

    let preamble = doc.preamble;
    if (titleBlock) preamble = upsertCommand(preamble, "title", titleBlock.text);
    if (authorBlock) preamble = upsertCommand(preamble, "author", authorBlock.text);

    const bodyLines: string[] = [];
    for (const block of doc.blocks) {
        if (block.kind === "title" || block.kind === "authors") continue;
        if (block.kind === "section") bodyLines.push(`\\section{${block.text}}`);
        else if (block.kind === "subsection") bodyLines.push(`\\subsection{${block.text}}`);
        else if (block.kind === "abstract") bodyLines.push(`\\begin{abstract}\n${block.text}\n\\end{abstract}`);
        else if (block.kind === "paragraph") bodyLines.push(block.text);
        else bodyLines.push(block.text);
        bodyLines.push("");
    }

    const footer = doc.footer.trim().startsWith("\\end{document}") ? doc.footer : "\n\\end{document}\n";
    return `${preamble.trimEnd()}\n\n${bodyLines.join("\n").trim()}\n\n${footer.trim()}\n`;
}
