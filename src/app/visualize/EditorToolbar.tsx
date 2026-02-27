"use client";

import { useCallback } from "react";
import { useReactFlow } from "@xyflow/react";

interface EditorToolbarProps {
    onAddNode: () => void;
    onExport: (format: "svg" | "png" | "pdf") => void;
    hasNodes: boolean;
}

export default function EditorToolbar({ onAddNode, onExport, hasNodes }: EditorToolbarProps) {
    const { fitView, deleteElements, getNodes, getEdges } = useReactFlow();

    const handleDeleteSelected = useCallback(() => {
        const selectedNodes = getNodes().filter((n) => n.selected);
        const selectedEdges = getEdges().filter((e) => e.selected);
        if (selectedNodes.length > 0 || selectedEdges.length > 0) {
            deleteElements({ nodes: selectedNodes, edges: selectedEdges });
        }
    }, [getNodes, getEdges, deleteElements]);

    const handleFitView = useCallback(() => {
        fitView({ padding: 0.2, duration: 300 });
    }, [fitView]);

    return (
        <div style={toolbarStyle}>
            <div style={groupStyle}>
                <button onClick={onAddNode} style={btnStyle} title="Add new node">
                    <span style={iconStyle}>＋</span> Add Node
                </button>
                <button onClick={handleDeleteSelected} style={btnStyle} title="Delete selected nodes/edges">
                    <span style={iconStyle}>🗑</span> Delete
                </button>
            </div>

            <div style={separatorStyle} />

            <div style={groupStyle}>
                <button onClick={handleFitView} style={btnStyle} title="Fit view to content">
                    <span style={iconStyle}>⊞</span> Fit
                </button>
            </div>

            {hasNodes && (
                <>
                    <div style={separatorStyle} />
                    <div style={groupStyle}>
                        <span style={{ fontSize: "0.72rem", color: "#9ca1ae", textTransform: "uppercase", letterSpacing: "0.04em", fontWeight: 600 }}>
                            Export
                        </span>
                        <button onClick={() => onExport("svg")} style={exportBtnStyle}>SVG</button>
                        <button onClick={() => onExport("png")} style={exportBtnStyle}>PNG</button>
                        <button onClick={() => onExport("pdf")} style={exportBtnStyle}>PDF</button>
                    </div>
                </>
            )}
        </div>
    );
}

/* ── Inline Styles ── */
const toolbarStyle: React.CSSProperties = {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    padding: "6px 12px",
    background: "#ffffff",
    borderBottom: "1px solid #e5e7eb",
    flexShrink: 0,
    flexWrap: "wrap",
};

const groupStyle: React.CSSProperties = {
    display: "flex",
    alignItems: "center",
    gap: "4px",
};

const separatorStyle: React.CSSProperties = {
    width: "1px",
    height: "24px",
    background: "#e5e7eb",
    margin: "0 4px",
};

const btnStyle: React.CSSProperties = {
    display: "inline-flex",
    alignItems: "center",
    gap: "4px",
    padding: "5px 10px",
    border: "1px solid #e5e7eb",
    borderRadius: "6px",
    background: "#fff",
    fontFamily: "Inter, sans-serif",
    fontSize: "0.8rem",
    fontWeight: 500,
    color: "#1a1d23",
    cursor: "pointer",
    transition: "all 150ms ease",
};

const iconStyle: React.CSSProperties = {
    fontSize: "0.9rem",
};

const exportBtnStyle: React.CSSProperties = {
    ...btnStyle,
    padding: "4px 8px",
    fontSize: "0.72rem",
    fontWeight: 600,
    color: "#2c6a73",
    borderColor: "#b8d8e0",
    background: "#f0f9fa",
};
