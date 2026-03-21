"use client";

import { useMemo, useState } from "react";

type BibliographyPanelProps = {
    bibContent: string;
    onChange: (next: string) => void;
    onInsertCitation: (key: string) => void;
};

function extractBibKeys(raw: string): string[] {
    const out: string[] = [];
    const re = /@\w+\s*\{\s*([^,\s]+)\s*,/g;
    let match: RegExpExecArray | null = re.exec(raw);
    while (match) {
        out.push(match[1]);
        match = re.exec(raw);
    }
    return out;
}

export default function BibliographyPanel({ bibContent, onChange, onInsertCitation }: BibliographyPanelProps) {
    const keys = useMemo(() => extractBibKeys(bibContent), [bibContent]);
    const [search, setSearch] = useState("");
    const filtered = keys.filter((k) => k.toLowerCase().includes(search.toLowerCase()));

    return (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 260px", minHeight: "260px", borderTop: "1px solid #d1d5db" }}>
            <textarea
                value={bibContent}
                onChange={(e) => onChange(e.target.value)}
                style={{
                    border: "none",
                    borderRight: "1px solid #d1d5db",
                    padding: "0.75rem",
                    fontFamily: "var(--font-mono)",
                    fontSize: "0.78rem",
                    resize: "none",
                    outline: "none",
                }}
            />
            <div style={{ padding: "0.65rem", background: "#fff", overflow: "auto" }}>
                <div style={{ fontSize: "0.76rem", fontWeight: 700, marginBottom: "0.45rem" }}>BibTeX Entries</div>
                <input className="input" placeholder="Search key..." value={search} onChange={(e) => setSearch(e.target.value)} />
                <div style={{ marginTop: "0.55rem", display: "grid", gap: "0.35rem" }}>
                    {filtered.map((key) => (
                        <div key={key} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", border: "1px solid #e5e7eb", borderRadius: "6px", padding: "0.3rem 0.45rem" }}>
                            <code style={{ fontSize: "0.72rem" }}>{key}</code>
                            <button className="btn btn-secondary" onClick={() => onInsertCitation(key)}>
                                Cite
                            </button>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

