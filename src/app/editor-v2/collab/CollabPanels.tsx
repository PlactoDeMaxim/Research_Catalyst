"use client";

import { useState } from "react";

type Snapshot = { id: string; ts: number; note: string; content: string };

type CollabPanelsProps = {
    currentContent: string;
    onRestoreVersion: (content: string) => void;
};

export default function CollabPanels({ currentContent, onRestoreVersion }: CollabPanelsProps) {
    const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
    const [shareOpen, setShareOpen] = useState(false);

    const [shareLink] = useState(
        () => `https://research-catalyst.local/share/${Math.random().toString(36).slice(2, 10)}`
    );

    return (
        <div style={{ borderTop: "1px solid #d1d5db", background: "#fff", padding: "0.55rem 0.65rem", display: "grid", gap: "0.55rem" }}>
            <div style={{ display: "flex", gap: "0.45rem" }}>
                <button className="btn btn-secondary" onClick={() => setShareOpen(true)}>
                    Share
                </button>
                <button
                    className="btn btn-secondary"
                    onClick={() =>
                        setSnapshots((prev) => [
                            {
                                id: `${Date.now()}`,
                                ts: Date.now(),
                                note: "Auto snapshot",
                                content: currentContent,
                            },
                            ...prev,
                        ])
                    }
                >
                    Snapshot
                </button>
            </div>
            <div style={{ maxHeight: "140px", overflow: "auto" }}>
                {snapshots.map((snap) => (
                    <div key={snap.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", border: "1px solid #e5e7eb", borderRadius: "6px", padding: "0.25rem 0.45rem", marginBottom: "0.3rem" }}>
                        <span style={{ fontSize: "0.72rem" }}>{new Date(snap.ts).toLocaleString()}</span>
                        <button className="btn btn-ghost" onClick={() => onRestoreVersion(snap.content)}>
                            Restore
                        </button>
                    </div>
                ))}
            </div>
            {shareOpen && (
                <div style={{ border: "1px solid #d1d5db", borderRadius: "8px", padding: "0.6rem", background: "#f9fafb" }}>
                    <div style={{ fontSize: "0.74rem", marginBottom: "0.3rem" }}>Share Link (UI only)</div>
                    <code style={{ display: "block", fontSize: "0.72rem", marginBottom: "0.4rem" }}>{shareLink}</code>
                    <button
                        className="btn btn-secondary"
                        onClick={async () => {
                            await navigator.clipboard.writeText(shareLink);
                            setShareOpen(false);
                        }}
                    >
                        Copy Link
                    </button>
                </div>
            )}
        </div>
    );
}

