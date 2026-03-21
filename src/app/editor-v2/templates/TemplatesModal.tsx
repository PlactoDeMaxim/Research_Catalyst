"use client";

import { useMemo, useState } from "react";

export type TemplateItem = {
    id: string;
    title: string;
    category: string;
    description: string;
    tags: string[];
    boilerplate: string;
};

const TEMPLATE_ITEMS: TemplateItem[] = [
    {
        id: "ieee-conference",
        title: "IEEE Conference Paper",
        category: "Academic Papers",
        description: "Two-column conference format with abstract and references.",
        tags: ["IEEE", "Two-column", "Academic"],
        boilerplate: `\\documentclass[conference]{IEEEtran}
\\usepackage{amsmath,graphicx,cite}
\\title{Paper Title}
\\author{Author Name}
\\begin{document}
\\maketitle
\\begin{abstract}Write abstract.\\end{abstract}
\\section{Introduction}
\\section{Related Work}
\\section{Methodology}
\\section{Results}
\\section{Conclusion}
\\begin{thebibliography}{1}
\\bibitem{ref1} Placeholder reference.
\\end{thebibliography}
\\end{document}`,
    },
    {
        id: "acm-sigconf",
        title: "ACM SIGCONF",
        category: "Academic Papers",
        description: "ACM proceedings style with structured sections.",
        tags: ["ACM", "SIGCONF"],
        boilerplate: `\\documentclass[sigconf]{acmart}
\\title{Paper Title}
\\author{Author Name}
\\begin{document}
\\begin{abstract}Write abstract.\\end{abstract}
\\maketitle
\\section{Introduction}
\\section{Method}
\\section{Evaluation}
\\section{Conclusion}
\\bibliographystyle{ACM-Reference-Format}
\\bibliography{bibliography}
\\end{document}`,
    },
    {
        id: "phd-thesis",
        title: "PhD Thesis",
        category: "Thesis & Dissertation",
        description: "Chapter-based thesis template.",
        tags: ["Thesis", "Chapter-based"],
        boilerplate: `\\documentclass[12pt]{report}
\\title{Thesis Title}
\\author{Candidate Name}
\\begin{document}
\\maketitle
\\tableofcontents
\\chapter{Introduction}
\\chapter{Literature Review}
\\chapter{Methodology}
\\chapter{Results}
\\chapter{Conclusion}
\\end{document}`,
    },
];

type TemplatesModalProps = {
    open: boolean;
    onClose: () => void;
    onUseTemplate: (item: TemplateItem) => void;
};

export default function TemplatesModal({ open, onClose, onUseTemplate }: TemplatesModalProps) {
    const [query, setQuery] = useState("");
    const [category, setCategory] = useState("All");

    const categories = useMemo(
        () => ["All", ...Array.from(new Set(TEMPLATE_ITEMS.map((t) => t.category)))],
        []
    );
    const filtered = useMemo(
        () =>
            TEMPLATE_ITEMS.filter((t) => {
                const byCategory = category === "All" || t.category === category;
                const q = query.trim().toLowerCase();
                const byQuery = !q || t.title.toLowerCase().includes(q) || t.tags.join(" ").toLowerCase().includes(q);
                return byCategory && byQuery;
            }),
        [category, query]
    );

    if (!open) return null;
    return (
        <div
            style={{ position: "fixed", inset: 0, background: "rgba(15,23,42,0.55)", zIndex: 1300, display: "grid", placeItems: "center" }}
            onClick={onClose}
        >
            <div
                onClick={(e) => e.stopPropagation()}
                style={{ width: "min(1100px, 95vw)", height: "min(85vh, 860px)", background: "#fff", borderRadius: "12px", overflow: "hidden", display: "grid", gridTemplateRows: "auto auto 1fr" }}
            >
                <div style={{ padding: "0.85rem 1rem", borderBottom: "1px solid #e5e7eb", fontWeight: 600 }}>Templates Gallery</div>
                <div style={{ padding: "0.65rem 1rem", display: "flex", gap: "0.55rem", borderBottom: "1px solid #e5e7eb" }}>
                    <input className="input" placeholder="Search templates..." value={query} onChange={(e) => setQuery(e.target.value)} />
                    <select className="input" style={{ maxWidth: "260px" }} value={category} onChange={(e) => setCategory(e.target.value)}>
                        {categories.map((c) => (
                            <option key={c}>{c}</option>
                        ))}
                    </select>
                </div>
                <div style={{ padding: "1rem", overflow: "auto", display: "grid", gap: "0.8rem", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))" }}>
                    {filtered.map((item) => (
                        <div key={item.id} style={{ border: "1px solid #d1d5db", borderRadius: "10px", overflow: "hidden", background: "#fff" }}>
                            <div style={{ height: "92px", background: "linear-gradient(120deg,#0f172a,#334155)", color: "#e2e8f0", display: "grid", placeItems: "center", fontWeight: 600 }}>
                                {item.title}
                            </div>
                            <div style={{ padding: "0.7rem" }}>
                                <div style={{ fontWeight: 600, fontSize: "0.85rem", marginBottom: "0.2rem" }}>{item.title}</div>
                                <div style={{ color: "#6b7280", fontSize: "0.75rem", minHeight: "34px" }}>{item.description}</div>
                                <div style={{ display: "flex", gap: "0.35rem", marginTop: "0.45rem", flexWrap: "wrap" }}>
                                    {item.tags.map((tag) => (
                                        <span key={tag} style={{ background: "#f3f4f6", borderRadius: "999px", fontSize: "0.68rem", padding: "2px 8px" }}>
                                            {tag}
                                        </span>
                                    ))}
                                </div>
                                <div style={{ display: "flex", gap: "0.45rem", marginTop: "0.65rem" }}>
                                    <button className="btn btn-primary" onClick={() => onUseTemplate(item)}>
                                        Use Template
                                    </button>
                                    <button className="btn btn-secondary" onClick={() => alert(item.boilerplate.slice(0, 500))}>
                                        Preview
                                    </button>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

