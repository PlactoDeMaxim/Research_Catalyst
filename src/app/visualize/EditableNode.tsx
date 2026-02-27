"use client";

import { useState, useRef, useEffect, useCallback, memo } from "react";
import { Handle, Position, NodeProps, useReactFlow } from "@xyflow/react";

/* ── Editable Node Component ──
   - Double-click label to edit inline
   - Hover to show delete button
   - Styled handles for connecting edges
   - Selection highlight with ring
*/
function EditableNodeInner({ id, data, selected }: NodeProps) {
    const [isEditing, setIsEditing] = useState(false);
    const [labelValue, setLabelValue] = useState(data.label as string);
    const [isHovered, setIsHovered] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);
    const { setNodes, deleteElements } = useReactFlow();

    // Keep local value in sync if parent changes it
    useEffect(() => {
        if (!isEditing) setLabelValue(data.label as string);
    }, [data.label, isEditing]);

    useEffect(() => {
        if (isEditing && inputRef.current) {
            inputRef.current.focus();
            inputRef.current.select();
        }
    }, [isEditing]);

    const commitEdit = useCallback(() => {
        setIsEditing(false);
        const trimmed = labelValue.trim() || "Node";
        setNodes((nds) =>
            nds.map((n) =>
                n.id === id ? { ...n, data: { ...n.data, label: trimmed } } : n
            )
        );
    }, [id, labelValue, setNodes]);

    const handleDoubleClick = useCallback((e: React.MouseEvent) => {
        e.stopPropagation();
        setIsEditing(true);
    }, []);

    const handleKeyDown = useCallback(
        (e: React.KeyboardEvent) => {
            e.stopPropagation(); // prevent ReactFlow from intercepting keys
            if (e.key === "Enter") commitEdit();
            if (e.key === "Escape") {
                setLabelValue(data.label as string);
                setIsEditing(false);
            }
        },
        [commitEdit, data.label]
    );

    const handleDelete = useCallback(
        (e: React.MouseEvent) => {
            e.stopPropagation();
            e.preventDefault();
            deleteElements({ nodes: [{ id }] });
        },
        [id, deleteElements]
    );

    const nodeColor = (data.color as string) || "#e8f4f6";
    const isNew = (data.isNew as boolean) || false;

    return (
        <div
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
            onDoubleClick={handleDoubleClick}
            style={{
                background: nodeColor,
                border: `2px solid ${selected ? "#2c6a73" : "#b8d8e0"}`,
                borderRadius: "10px",
                padding: "10px 20px",
                minWidth: "90px",
                maxWidth: "240px",
                fontSize: "13px",
                fontFamily: "Inter, sans-serif",
                fontWeight: 500,
                color: "#1a1d23",
                position: "relative",
                boxShadow: selected
                    ? "0 0 0 3px rgba(44, 106, 115, 0.2), 0 4px 12px rgba(0,0,0,0.08)"
                    : isNew
                        ? "0 0 0 2px rgba(202, 154, 42, 0.3), 0 2px 8px rgba(0,0,0,0.06)"
                        : "0 1px 4px rgba(0,0,0,0.06)",
                transition: "box-shadow 150ms ease, border-color 150ms ease",
                cursor: isEditing ? "text" : "grab",
                userSelect: isEditing ? "text" : "none",
            }}
        >
            {/* Delete button — shows on hover */}
            {(isHovered || selected) && !isEditing && (
                <button
                    onClick={handleDelete}
                    onMouseDown={(e) => e.stopPropagation()}
                    style={{
                        position: "absolute",
                        top: "-10px",
                        right: "-10px",
                        width: "22px",
                        height: "22px",
                        borderRadius: "50%",
                        background: "#ef4444",
                        color: "#fff",
                        border: "2px solid #fff",
                        fontSize: "12px",
                        lineHeight: "1",
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        boxShadow: "0 2px 6px rgba(239, 68, 68, 0.3)",
                        zIndex: 10,
                        padding: 0,
                        transition: "transform 100ms ease",
                    }}
                    title="Delete node"
                >
                    ×
                </button>
            )}

            {/* Target handle (top) */}
            <Handle
                type="target"
                position={Position.Top}
                style={{
                    width: "12px",
                    height: "12px",
                    background: selected || isHovered ? "#2c6a73" : "#b8d8e0",
                    border: "2px solid #fff",
                    top: "-6px",
                    transition: "background 150ms ease",
                }}
            />

            {/* Label or editing input */}
            {isEditing ? (
                <input
                    ref={inputRef}
                    value={labelValue}
                    onChange={(e) => setLabelValue(e.target.value)}
                    onBlur={commitEdit}
                    onKeyDown={handleKeyDown}
                    onMouseDown={(e) => e.stopPropagation()}
                    style={{
                        background: "#fff",
                        border: "1px solid #2c6a73",
                        borderRadius: "4px",
                        outline: "none",
                        font: "inherit",
                        fontWeight: "inherit",
                        color: "inherit",
                        width: "100%",
                        textAlign: "center",
                        padding: "2px 6px",
                    }}
                />
            ) : (
                <div
                    style={{
                        textAlign: "center",
                        lineHeight: 1.4,
                        wordBreak: "break-word",
                    }}
                >
                    {data.label as string}
                    {isNew && (
                        <div style={{ fontSize: "0.65rem", color: "#9ca1ae", marginTop: "2px" }}>
                            double-click to edit
                        </div>
                    )}
                </div>
            )}

            {/* Source handle (bottom) */}
            <Handle
                type="source"
                position={Position.Bottom}
                style={{
                    width: "12px",
                    height: "12px",
                    background: selected || isHovered ? "#2c6a73" : "#b8d8e0",
                    border: "2px solid #fff",
                    bottom: "-6px",
                    transition: "background 150ms ease",
                }}
            />

            {/* Left + Right handles for horizontal connections */}
            <Handle
                type="target"
                position={Position.Left}
                id="left"
                style={{
                    width: "10px",
                    height: "10px",
                    background: selected || isHovered ? "#2c6a73" : "#b8d8e0",
                    border: "2px solid #fff",
                    left: "-5px",
                    transition: "background 150ms ease",
                    opacity: isHovered ? 1 : 0,
                }}
            />
            <Handle
                type="source"
                position={Position.Right}
                id="right"
                style={{
                    width: "10px",
                    height: "10px",
                    background: selected || isHovered ? "#2c6a73" : "#b8d8e0",
                    border: "2px solid #fff",
                    right: "-5px",
                    transition: "background 150ms ease",
                    opacity: isHovered ? 1 : 0,
                }}
            />
        </div>
    );
}

export const EditableNode = memo(EditableNodeInner);

export const nodeTypes = {
    editableNode: EditableNode,
};
