"use client";

import { useMemo } from "react";
import katex from "katex";
import "katex/dist/katex.min.css";
import styles from "./LatexPreview.module.css";

interface LatexPreviewProps {
    source: string;
    templateId?: string;
}

function renderMath(tex: string, displayMode: boolean): string {
    try {
        return katex.renderToString(tex, {
            displayMode,
            throwOnError: false,
            trust: true,
        });
    } catch {
        return `<span class="math-error">${tex}</span>`;
    }
}

function latexToHtml(source: string, templateId: string): string {
    let html = source;

    // Extract and protect math blocks first
    const mathBlocks: string[] = [];

    // Display math: \[ ... \] and $$ ... $$
    html = html.replace(/\\\[([\s\S]*?)\\\]/g, (_, tex) => {
        const idx = mathBlocks.length;
        mathBlocks.push(renderMath(tex.trim(), true));
        return `%%MATH_BLOCK_${idx}%%`;
    });
    html = html.replace(/\$\$([\s\S]*?)\$\$/g, (_, tex) => {
        const idx = mathBlocks.length;
        mathBlocks.push(renderMath(tex.trim(), true));
        return `%%MATH_BLOCK_${idx}%%`;
    });

    // Inline math: $ ... $
    html = html.replace(/\$([^\$\n]+?)\$/g, (_, tex) => {
        const idx = mathBlocks.length;
        mathBlocks.push(renderMath(tex.trim(), false));
        return `%%MATH_BLOCK_${idx}%%`;
    });

    // Escape HTML
    html = html
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

    // --- Template-aware section numbering ---
    let sectionCounter = 0;
    let subsectionCounter = 0;

    // \title{...}
    html = html.replace(
        /\\title\{([^}]*)\}/g,
        '<h1 class="doc-title">$1</h1>'
    );

    // \author{...}
    html = html.replace(
        /\\author\{([^}]*)\}/g,
        (_: string, authors: string) => {
            const authorList = authors.split(",").map((a: string) => a.trim());
            if (templateId === "ieee" || templateId === "acm") {
                return `<div class="doc-authors">${authorList
                    .map(
                        (a: string) =>
                            `<div class="author-block"><span class="author-name">${a}</span><span class="author-affil">University Department</span></div>`
                    )
                    .join("")}</div>`;
            }
            return `<p class="doc-author-line">${authors}</p>`;
        }
    );

    // \date{...}
    html = html.replace(
        /\\date\{([^}]*)\}/g,
        '<p class="doc-date">$1</p>'
    );

    html = html.replace(/\\today/g, new Date().toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" }));
    html = html.replace(/\\maketitle/g, "");

    // \begin{abstract}...\end{abstract}
    html = html.replace(
        /\\begin\{abstract\}([\s\S]*?)\\end\{abstract\}/g,
        (_: string, content: string) => {
            if (templateId === "ieee") {
                return `<div class="abstract-block"><p class="abstract-label"><em>Abstract</em>—</p><p class="abstract-text"><em>${content.trim()}</em></p></div>`;
            }
            if (templateId === "acm") {
                return `<div class="abstract-block acm-abstract"><h3>ABSTRACT</h3><p class="abstract-text">${content.trim()}</p></div>`;
            }
            return `<div class="abstract-block"><h3>Abstract</h3><p class="abstract-text">${content.trim()}</p></div>`;
        }
    );

    // --- Sections ---
    html = html.replace(
        /\\section\*?\{([^}]*)\}/g,
        (_: string, title: string) => {
            sectionCounter++;
            subsectionCounter = 0;
            if (templateId === "ieee") {
                return `<h2 class="doc-section"><span class="sec-num">${toRoman(sectionCounter)}.</span> ${title.toUpperCase()}</h2>`;
            }
            if (templateId === "acm") {
                return `<h2 class="doc-section"><span class="sec-num">${sectionCounter}</span> ${title.toUpperCase()}</h2>`;
            }
            if (templateId === "thesis") {
                return `<h2 class="doc-section"><span class="sec-num">Chapter ${sectionCounter}</span><br/>${title}</h2>`;
            }
            return `<h2 class="doc-section"><span class="sec-num">${sectionCounter}.</span> ${title}</h2>`;
        }
    );

    html = html.replace(
        /\\subsection\*?\{([^}]*)\}/g,
        (_: string, title: string) => {
            subsectionCounter++;
            if (templateId === "ieee") {
                return `<h3 class="doc-subsection"><em>${String.fromCharCode(64 + subsectionCounter)}. ${title}</em></h3>`;
            }
            return `<h3 class="doc-subsection"><span class="sec-num">${sectionCounter}.${subsectionCounter}</span> ${title}</h3>`;
        }
    );

    html = html.replace(
        /\\subsubsection\*?\{([^}]*)\}/g,
        '<h4 class="doc-subsubsection">$1</h4>'
    );

    // --- Text formatting ---
    html = html.replace(/\\textbf\{([^}]*)\}/g, "<strong>$1</strong>");
    html = html.replace(/\\textit\{([^}]*)\}/g, "<em>$1</em>");
    html = html.replace(/\\underline\{([^}]*)\}/g, "<u>$1</u>");
    html = html.replace(/\\texttt\{([^}]*)\}/g, "<code>$1</code>");
    html = html.replace(/\\emph\{([^}]*)\}/g, "<em>$1</em>");

    // --- Lists ---
    html = html.replace(
        /\\begin\{itemize\}([\s\S]*?)\\end\{itemize\}/g,
        (_, content) => {
            const items = content
                .split("\\item")
                .filter((s: string) => s.trim())
                .map((s: string) => `<li>${s.trim()}</li>`)
                .join("");
            return `<ul>${items}</ul>`;
        }
    );

    html = html.replace(
        /\\begin\{enumerate\}([\s\S]*?)\\end\{enumerate\}/g,
        (_, content) => {
            const items = content
                .split("\\item")
                .filter((s: string) => s.trim())
                .map((s: string) => `<li>${s.trim()}</li>`)
                .join("");
            return `<ol>${items}</ol>`;
        }
    );

    // --- Citations ---
    html = html.replace(
        /\\cite\{([^}]*)\}/g,
        (_: string, keys: string) => {
            const refs = keys.split(",").map((k: string, i: number) => i + 1);
            return `<span class="cite-ref">[${refs.join(", ")}]</span>`;
        }
    );

    html = html.replace(/\\ref\{([^}]*)\}/g, '<span class="cite-ref">$1</span>');
    html = html.replace(/\\label\{([^}]*)\}/g, "");

    // --- Figures ---
    html = html.replace(
        /\\begin\{figure\}[\s\S]*?\\caption\{([^}]*)\}[\s\S]*?\\end\{figure\}/g,
        (_: string, caption: string) => {
            return `<div class="figure-block"><div class="figure-placeholder"></div><p class="figure-caption"><strong>Fig. ${sectionCounter}.</strong> ${caption}</p></div>`;
        }
    );

    // --- Tables ---
    html = html.replace(
        /\\begin\{table\}[\s\S]*?\\caption\{([^}]*)\}[\s\S]*?\\end\{table\}/g,
        (_: string, caption: string) => {
            return `<div class="table-block"><div class="table-placeholder">TABLE</div><p class="table-caption"><strong>TABLE ${sectionCounter}.</strong> ${caption}</p></div>`;
        }
    );
    html = html.replace(
        /\\begin\{table\}[\s\S]*?\\end\{table\}/g,
        '<div class="table-block"><div class="table-placeholder">TABLE</div></div>'
    );

    // --- Remove preamble commands ---
    html = html.replace(/\\documentclass(\[.*?\])?\{[^}]*\}/g, "");
    html = html.replace(/\\usepackage(\[.*?\])?\{[^}]*\}/g, "");
    html = html.replace(/\\begin\{document\}/g, "");
    html = html.replace(/\\end\{document\}/g, "");
    html = html.replace(/\\bibliographystyle\{[^}]*\}/g, "");
    html = html.replace(/\\bibliography\{[^}]*\}/g, "");
    html = html.replace(/\\newcommand\{[^}]*\}\{[^}]*\}/g, "");

    // Line breaks
    html = html.replace(/\\\\/g, "<br/>");
    html = html.replace(/\\newline/g, "<br/>");
    html = html.replace(/\\noindent/g, "");
    html = html.replace(/\\vspace\{[^}]*\}/g, "");
    html = html.replace(/\\hspace\{[^}]*\}/g, "&nbsp;");

    // Comments
    html = html.replace(/^%.*$/gm, "");

    // Convert double newlines to paragraphs
    const blocks = html.split(/\n\s*\n/);
    html = blocks
        .map((block) => {
            const trimmed = block.trim();
            if (!trimmed) return "";
            if (
                trimmed.startsWith("<h") ||
                trimmed.startsWith("<div") ||
                trimmed.startsWith("<ul") ||
                trimmed.startsWith("<ol") ||
                trimmed.startsWith("<p class=")
            ) {
                return trimmed;
            }
            return `<p>${trimmed}</p>`;
        })
        .join("\n");

    // Restore math blocks
    mathBlocks.forEach((rendered, idx) => {
        html = html.replace(`%%MATH_BLOCK_${idx}%%`, rendered);
    });

    // Clean up remaining backslash commands
    html = html.replace(/\\[a-zA-Z]+(\[[^\]]*\])?\{[^}]*\}/g, "");
    html = html.replace(/\\[a-zA-Z]+/g, "");

    return html;
}

function toRoman(num: number): string {
    const vals = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1];
    const syms = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"];
    let result = "";
    for (let i = 0; i < vals.length; i++) {
        while (num >= vals[i]) {
            result += syms[i];
            num -= vals[i];
        }
    }
    return result;
}

export default function LatexPreview({ source, templateId = "arxiv" }: LatexPreviewProps) {
    const rendered = useMemo(() => latexToHtml(source, templateId), [source, templateId]);

    return (
        <div className={styles.preview}>
            <div className={`${styles.paper} ${styles[templateId] || ""}`}>
                <div
                    className={styles.content}
                    dangerouslySetInnerHTML={{ __html: rendered }}
                />
            </div>
        </div>
    );
}
