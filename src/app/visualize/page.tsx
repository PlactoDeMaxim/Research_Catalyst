"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import styles from "./page.module.css";
import {
    ReactFlow,
    MiniMap,
    Controls,
    Background,
    Panel,
    addEdge,
    useNodesState,
    useEdgesState,
    ReactFlowProvider,
    useReactFlow,
    type Node,
    type Edge,
    type Connection,
    BackgroundVariant,
    MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { nodeTypes } from "./EditableNode";
import dagre from "dagre";
import { TransformWrapper, TransformComponent } from "react-zoom-pan-pinch";

const API_BASE = "http://localhost:8000/api/visualization";

/* ── Types ── */
type InputMode = "ai-text" | "ai-code" | "manual";
type ViewTab = "editor" | "preview";

/* ── Graphviz WASM Hook ── */
function useGraphviz() {
    const gvRef = useRef<any>(null);
    const [ready, setReady] = useState(false);

    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                const { Graphviz } = await import("@hpcc-js/wasm-graphviz");
                const inst = await Graphviz.load();
                if (!cancelled) { gvRef.current = inst; setReady(true); }
            } catch (err) { console.error("Graphviz WASM load error:", err); }
        })();
        return () => { cancelled = true; };
    }, []);

    const render = useCallback((dot: string, engine = "dot"): string | null => {
        if (!gvRef.current) return null;
        try { return gvRef.current.layout(dot, "svg", engine); }
        catch { return null; }
    }, []);

    return { render, ready };
}

/* ── Auto-layout helper (Hierarchical via Dagre) ── */
function getLayoutedElements(nodes: Node[], edges: Edge[], direction = "TB"): Node[] {
    const dagreGraph = new dagre.graphlib.Graph();
    dagreGraph.setDefaultEdgeLabel(() => ({}));
    dagreGraph.setGraph({ rankdir: direction, nodesep: 60, ranksep: 80 });

    nodes.forEach((node) => {
        // Approximate dimensions of the EditableNode
        dagreGraph.setNode(node.id, { width: 160, height: 60 });
    });

    edges.forEach((edge) => {
        dagreGraph.setEdge(edge.source, edge.target);
    });

    dagre.layout(dagreGraph);

    return nodes.map((node) => {
        const nodeWithPosition = dagreGraph.node(node.id);
        return {
            ...node,
            position: {
                x: nodeWithPosition.x - 80,
                y: nodeWithPosition.y - 30,
            },
        };
    });
}

function createUnlayoutedNodes(labels: string[]): Node[] {
    return labels.map((label, i) => ({
        id: `node-${i}`,
        type: "editableNode",
        data: { label, color: "#e8f4f6" },
        position: { x: 0, y: 0 },
    }));
}

/* ── Convert React Flow state → DOT ── */
function flowToDot(nodes: Node[], edges: Edge[], title?: string): string {
    const lines: string[] = ["digraph G {"];
    lines.push('  rankdir=TB;');
    lines.push('  node [shape=box, style="rounded,filled", fillcolor="#e8f4f6", fontname="Inter", fontsize=11, color="#2c6a73"];');
    lines.push('  edge [color="#5e6472", fontname="Inter", fontsize=9];');
    if (title) {
        lines.push(`  labelloc="t";`);
        lines.push(`  label="${title}";`);
        lines.push(`  fontname="Inter";`);
        lines.push(`  fontsize=14;`);
    }

    for (const node of nodes) {
        const label = (node.data?.label as string) || node.id;
        const safeId = node.id.replace(/[^a-zA-Z0-9_]/g, "_");
        lines.push(`  ${safeId} [label="${label}"];`);
    }

    for (const edge of edges) {
        const src = edge.source.replace(/[^a-zA-Z0-9_]/g, "_");
        const tgt = edge.target.replace(/[^a-zA-Z0-9_]/g, "_");
        const lbl = edge.label ? ` [label="${edge.label}"]` : "";
        lines.push(`  ${src} -> ${tgt}${lbl};`);
    }

    lines.push("}");
    return lines.join("\n");
}


/* ── Inner Component (needs ReactFlowProvider) ── */
function VisualizationStudioInner() {
    const { fitView, getNodes, getEdges, screenToFlowPosition } = useReactFlow();

    // State
    const [inputMode, setInputMode] = useState<InputMode>("ai-text");
    const [viewTab, setViewTab] = useState<ViewTab>("editor");
    const [sidebarOpen, setSidebarOpen] = useState(true);
    const [renderEngine, setRenderEngine] = useState("dot");

    // AI Text
    const [aiText, setAiText] = useState("");
    const [aiTextType, setAiTextType] = useState("flowchart");

    // AI Code
    const [aiCode, setAiCode] = useState("");
    const [aiCodeLang, setAiCodeLang] = useState("python");

    // Manual
    const [manualNodes, setManualNodes] = useState("Problem\nLiterature Review\nMethodology\nResults\nConclusion");
    const [manualEdges, setManualEdges] = useState("Problem,Literature Review\nLiterature Review,Methodology\nMethodology,Results\nResults,Conclusion");
    const [manualTitle, setManualTitle] = useState("Research Pipeline");

    // React Flow
    const [rfNodes, setRfNodes, onNodesChange] = useNodesState<Node>([]);
    const [rfEdges, setRfEdges, onEdgesChange] = useEdgesState<Edge>([]);

    // Graphviz preview
    const { render: renderGraphviz, ready: gvReady } = useGraphviz();
    const [previewSvg, setPreviewSvg] = useState("");

    // Loading / Error
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [statusMsg, setStatusMsg] = useState("");

    // Node counter for unique IDs
    const nodeCounter = useRef(100);

    /* ── Edge connection handler ── */
    const onConnect = useCallback(
        (params: Connection) =>
            setRfEdges((eds) =>
                addEdge(
                    {
                        ...params,
                        animated: true,
                        style: { stroke: "#2c6a73", strokeWidth: 2 },
                        markerEnd: { type: MarkerType.ArrowClosed, color: "#2c6a73", width: 16, height: 16 },
                    },
                    eds
                )
            ),
        [setRfEdges]
    );

    /* ── Autolayout Current Graph ── */
    const handleAutoLayout = useCallback(() => {
        const layouted = getLayoutedElements(getNodes(), getEdges(), "TB");
        setRfNodes(layouted);
        setTimeout(() => fitView({ padding: 0.2, duration: 400 }), 50);
        setStatusMsg("Applied hierarchical layout");
    }, [getNodes, getEdges, setRfNodes, fitView]);

    /* ── Add Node (directly on canvas) ── */
    const handleAddNode = useCallback(() => {
        const id = `node-${nodeCounter.current++}`;
        const newNode: Node = {
            id,
            type: "editableNode",
            data: { label: "New Node", color: "#fef9ee", isNew: true },
            position: {
                x: 200 + Math.random() * 200,
                y: 200 + Math.random() * 150,
            },
        };
        setRfNodes((nds) => [...nds, newNode]);
        setStatusMsg("Node added — double-click to rename");
    }, [setRfNodes]);

    /* ── Delete selected ── */
    const handleDeleteSelected = useCallback(() => {
        const selectedNodes = getNodes().filter((n) => n.selected);
        const selectedEdges = getEdges().filter((e) => e.selected);
        if (selectedNodes.length === 0 && selectedEdges.length === 0) {
            setStatusMsg("Select nodes or edges first (click to select)");
            return;
        }
        setRfNodes((nds) => nds.filter((n) => !n.selected));
        setRfEdges((eds) => eds.filter((e) => !e.selected));
        setStatusMsg(`Deleted ${selectedNodes.length} nodes, ${selectedEdges.length} edges`);
    }, [getNodes, getEdges, setRfNodes, setRfEdges]);

    /* ── Generate Graphviz Preview ── */
    const handlePreview = useCallback(() => {
        const currentNodes = getNodes();
        const currentEdges = getEdges();
        if (currentNodes.length === 0) {
            setStatusMsg("Add some nodes first");
            return;
        }
        const dot = flowToDot(currentNodes, currentEdges, manualTitle);
        const svg = renderGraphviz(dot, renderEngine);
        if (svg) {
            // Make SVG fluid by removing explicit width/height
            // Graphviz produces <svg width="123pt" height="456pt" viewBox="..." ...>
            const fluidSvg = svg
                .replace(/width="[^"]*"/i, '')
                .replace(/height="[^"]*"/i, '');
            setPreviewSvg(fluidSvg);
            setViewTab("preview");
            setError(null);
        } else {
            setError("Failed to render preview");
        }
    }, [getNodes, getEdges, renderGraphviz, renderEngine, manualTitle]);

    /* ── AI Text to Diagram ── */
    const handleAiText = useCallback(async () => {
        if (!aiText.trim()) return;
        setLoading(true);
        setError(null);
        setStatusMsg("AI is analyzing your text...");

        try {
            const resp = await fetch(`${API_BASE}/ai/text-to-diagram`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text: aiText, diagram_type: aiTextType, format: "graphviz" }),
            });
            if (!resp.ok) {
                const detail = await resp.json().catch(() => ({}));
                throw new Error(detail.detail || `Generation failed: ${resp.status}`);
            }
            const data = await resp.json();

            // Structure graph
            const nodeLabels = (data.nodes || []).map((n: any) => n.label || n);
            const unlayoutedNodes = createUnlayoutedNodes(nodeLabels);
            const flowEdges: Edge[] = (data.edges || []).map((e: any, i: number) => ({
                id: e.id || `edge-${i}`,
                source: e.source || `node-0`,
                target: e.target || `node-0`,
                label: e.label || "",
                animated: true,
                style: { stroke: "#2c6a73", strokeWidth: 2 },
                markerEnd: { type: MarkerType.ArrowClosed, color: "#2c6a73", width: 16, height: 16 },
            }));

            // Apply Dagre hierarchy layout
            const layoutedNodes = getLayoutedElements(unlayoutedNodes, flowEdges, "TB");

            setRfNodes(layoutedNodes);
            setRfEdges(flowEdges);
            setViewTab("editor");
            setStatusMsg(`AI generated ${layoutedNodes.length} nodes — edit them interactively!`);
            nodeCounter.current = layoutedNodes.length + 10;

            setTimeout(() => fitView({ padding: 0.2, duration: 400 }), 100);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "AI text generation failed");
            setStatusMsg("");
        } finally {
            setLoading(false);
        }
    }, [aiText, aiTextType, setRfNodes, setRfEdges, fitView]);

    /* ── AI Code to Diagram ── */
    const handleAiCode = useCallback(async () => {
        if (!aiCode.trim()) return;
        setLoading(true);
        setError(null);
        setStatusMsg("AI is analyzing your code...");

        try {
            const resp = await fetch(`${API_BASE}/ai/code-to-diagram`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ code: aiCode, language: aiCodeLang, diagram_type: "architecture", format: "graphviz" }),
            });
            if (!resp.ok) {
                const detail = await resp.json().catch(() => ({}));
                throw new Error(detail.detail || `Code analysis failed: ${resp.status}`);
            }
            const data = await resp.json();

            const nodeLabels = (data.nodes || []).map((n: any) => n.label || n);
            const unlayoutedNodes = createUnlayoutedNodes(nodeLabels);
            const flowEdges: Edge[] = (data.edges || []).map((e: any, i: number) => ({
                id: e.id || `edge-${i}`,
                source: e.source || `node-0`,
                target: e.target || `node-0`,
                label: e.label || "",
                animated: true,
                style: { stroke: "#2c6a73", strokeWidth: 2 },
                markerEnd: { type: MarkerType.ArrowClosed, color: "#2c6a73", width: 16, height: 16 },
            }));

            const layoutedNodes = getLayoutedElements(unlayoutedNodes, flowEdges, "TB");

            setRfNodes(layoutedNodes);
            setRfEdges(flowEdges);
            setViewTab("editor");
            setStatusMsg(`AI generated architecture with ${layoutedNodes.length} components`);
            nodeCounter.current = layoutedNodes.length + 10;

            setTimeout(() => fitView({ padding: 0.2, duration: 400 }), 100);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "AI code analysis failed");
            setStatusMsg("");
        } finally {
            setLoading(false);
        }
    }, [aiCode, aiCodeLang, setRfNodes, setRfEdges, fitView]);

    /* ── Manual Generate ── */
    const handleManual = useCallback(async () => {
        setLoading(true);
        setError(null);
        setStatusMsg("Generating diagram...");

        try {
            const nodes = manualNodes.split("\n").map((n) => n.trim()).filter(Boolean);
            const edges = manualEdges.split("\n").map((e) => e.split(",").map((s) => s.trim())).filter((e) => e.length >= 2);

            const unlayoutedNodes = createUnlayoutedNodes(nodes);
            const flowEdges: Edge[] = edges.map((e, i) => {
                const srcIdx = nodes.indexOf(e[0]);
                const tgtIdx = nodes.indexOf(e[1]);
                return {
                    id: `edge-${i}`,
                    source: `node-${srcIdx >= 0 ? srcIdx : 0}`,
                    target: `node-${tgtIdx >= 0 ? tgtIdx : 0}`,
                    label: e[2] || "",
                    animated: true,
                    style: { stroke: "#2c6a73", strokeWidth: 2 },
                    markerEnd: { type: MarkerType.ArrowClosed, color: "#2c6a73", width: 16, height: 16 },
                };
            });

            const layoutedNodes = getLayoutedElements(unlayoutedNodes, flowEdges, "TB");

            setRfNodes(layoutedNodes);
            setRfEdges(flowEdges);
            setViewTab("editor");
            setStatusMsg(`Generated ${layoutedNodes.length} nodes — drag, edit, connect!`);
            nodeCounter.current = layoutedNodes.length + 10;

            setTimeout(() => fitView({ padding: 0.2, duration: 400 }), 100);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Generation failed");
            setStatusMsg("");
        } finally {
            setLoading(false);
        }
    }, [manualNodes, manualEdges, setRfNodes, setRfEdges, fitView]);

    /* ── Export ── */
    const handleExport = useCallback((format: "svg" | "png") => {
        // Generate the beautiful Graphviz version for export
        const currentNodes = getNodes();
        const currentEdges = getEdges();
        if (currentNodes.length === 0) {
            setError("No diagram to export");
            return;
        }

        const dot = flowToDot(currentNodes, currentEdges, manualTitle);
        const svg = renderGraphviz(dot, renderEngine);
        if (!svg) {
            setError("Export rendering failed");
            return;
        }

        if (format === "svg") {
            const blob = new Blob([svg], { type: "image/svg+xml" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url; a.download = "diagram.svg"; a.click();
            URL.revokeObjectURL(url);
            return;
        }

        // PNG via canvas
        const svgBlob = new Blob([svg], { type: "image/svg+xml;charset=utf-8" });
        const url = URL.createObjectURL(svgBlob);
        const img = new Image();
        img.onload = () => {
            const canvas = document.createElement("canvas");
            const scale = 2;
            canvas.width = img.width * scale;
            canvas.height = img.height * scale;
            const ctx = canvas.getContext("2d")!;
            ctx.scale(scale, scale);
            ctx.fillStyle = "white";
            ctx.fillRect(0, 0, img.width, img.height);
            ctx.drawImage(img, 0, 0);
            canvas.toBlob((blob) => {
                if (blob) {
                    const pngUrl = URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = pngUrl; a.download = "diagram.png"; a.click();
                    URL.revokeObjectURL(pngUrl);
                }
            }, "image/png");
            URL.revokeObjectURL(url);
        };
        img.src = url;
    }, [getNodes, getEdges, renderGraphviz, renderEngine, manualTitle]);

    /* ── Double-click on canvas → add node at that position ── */
    const onPaneDoubleClick = useCallback(
        (event: React.MouseEvent) => {
            const position = screenToFlowPosition({ x: event.clientX, y: event.clientY });
            const id = `node-${nodeCounter.current++}`;
            const newNode: Node = {
                id,
                type: "editableNode",
                data: { label: "New Node", color: "#fef9ee", isNew: true },
                position,
            };
            setRfNodes((nds) => [...nds, newNode]);
            setStatusMsg("Node added — double-click it to rename");
        },
        [screenToFlowPosition, setRfNodes]
    );

    return (
        <div className={styles.page}>
            {/* ── Header ── */}
            <div className={styles.header}>
                <div className={styles.headerLeft}>
                    <button className={styles.sidebarToggle} onClick={() => setSidebarOpen(!sidebarOpen)}>
                        {sidebarOpen ? "◀" : "▶"}
                    </button>
                    <div>
                        <h1 className={styles.title}>Visualization Studio</h1>
                        <p className={styles.subtitle}>
                            AI-powered diagrams • Drag nodes to move • Drag handles to connect • Double-click to edit labels
                        </p>
                    </div>
                </div>
                <div className={styles.headerRight}>
                    {statusMsg && (
                        <div className={styles.statusPill}>
                            {loading && <span className={styles.statusDot} />}
                            {statusMsg}
                        </div>
                    )}
                </div>
            </div>

            {/* ── Error ── */}
            {error && (
                <div className={styles.errorBanner}>
                    ⚠️ {error}
                    <button className={styles.errorClose} onClick={() => setError(null)}>✕</button>
                </div>
            )}

            {/* ── Main Layout ── */}
            <div className={styles.studio}>
                {/* LEFT SIDEBAR */}
                {sidebarOpen && (
                    <div className={styles.sidebar}>
                        <div className={styles.modeTabs}>
                            <button className={`${styles.modeTab} ${inputMode === "ai-text" ? styles.modeTabActive : ""}`} onClick={() => setInputMode("ai-text")}>🧠 AI Text</button>
                            <button className={`${styles.modeTab} ${inputMode === "ai-code" ? styles.modeTabActive : ""}`} onClick={() => setInputMode("ai-code")}>💻 AI Code</button>
                            <button className={`${styles.modeTab} ${inputMode === "manual" ? styles.modeTabActive : ""}`} onClick={() => setInputMode("manual")}>✏️ Manual</button>
                        </div>

                        <div className={styles.sidebarContent}>
                            {/* AI TEXT */}
                            {inputMode === "ai-text" && (
                                <div className={styles.inputSection}>
                                    <p className={styles.inputHint}>Paste research text or methodology — AI extracts a diagram you can then edit interactively.</p>
                                    <label className={styles.fieldLabel}>Diagram Type</label>
                                    <select className="input" value={aiTextType} onChange={(e) => setAiTextType(e.target.value)}>
                                        <option value="flowchart">Flowchart</option>
                                        <option value="architecture">Architecture</option>
                                        <option value="sequence">Sequence</option>
                                        <option value="methodology">Methodology</option>
                                    </select>
                                    <label className={styles.fieldLabel}>Research Text</label>
                                    <textarea className={`input ${styles.bigTextarea}`} value={aiText} onChange={(e) => setAiText(e.target.value)}
                                        placeholder={"Paste your research methodology, paper abstract, process description...\n\nExample:\nOur methodology begins with problem formulation, followed by literature review, experimental design, data collection, statistical analysis, and conclusions."} rows={10} />
                                    <button className={`btn btn-primary w-full ${styles.generateBtn}`} onClick={handleAiText} disabled={loading || !aiText.trim()}>
                                        {loading ? <><span className={styles.btnSpinner} /> Generating...</> : "🧠 Generate with AI"}
                                    </button>
                                </div>
                            )}

                            {/* AI CODE */}
                            {inputMode === "ai-code" && (
                                <div className={styles.inputSection}>
                                    <p className={styles.inputHint}>Paste source code — AI extracts architecture/dependency diagrams.</p>
                                    <label className={styles.fieldLabel}>Language</label>
                                    <select className="input" value={aiCodeLang} onChange={(e) => setAiCodeLang(e.target.value)}>
                                        <option value="python">Python</option>
                                        <option value="javascript">JavaScript</option>
                                        <option value="typescript">TypeScript</option>
                                        <option value="java">Java</option>
                                        <option value="c++">C++</option>
                                        <option value="go">Go</option>
                                        <option value="rust">Rust</option>
                                    </select>
                                    <label className={styles.fieldLabel}>Source Code</label>
                                    <textarea className={`input ${styles.bigTextarea} ${styles.codeTextarea}`} value={aiCode} onChange={(e) => setAiCode(e.target.value)}
                                        placeholder={"Paste your source code here..."} rows={10} />
                                    <button className={`btn btn-primary w-full ${styles.generateBtn}`} onClick={handleAiCode} disabled={loading || !aiCode.trim()}>
                                        {loading ? <><span className={styles.btnSpinner} /> Analyzing...</> : "💻 Analyze Code"}
                                    </button>
                                </div>
                            )}

                            {/* MANUAL */}
                            {inputMode === "manual" && (
                                <div className={styles.inputSection}>
                                    <p className={styles.inputHint}>Define nodes and edges manually.</p>
                                    <label className={styles.fieldLabel}>Title</label>
                                    <input className="input" value={manualTitle} onChange={(e) => setManualTitle(e.target.value)} />
                                    <label className={styles.fieldLabel}>Nodes (one per line)</label>
                                    <textarea className={`input ${styles.smallTextarea}`} value={manualNodes} onChange={(e) => setManualNodes(e.target.value)} rows={4} />
                                    <label className={styles.fieldLabel}>Edges (source,target per line)</label>
                                    <textarea className={`input ${styles.smallTextarea}`} value={manualEdges} onChange={(e) => setManualEdges(e.target.value)} rows={4} />
                                    <button className={`btn btn-primary w-full ${styles.generateBtn}`} onClick={handleManual} disabled={loading}>
                                        {loading ? <><span className={styles.btnSpinner} /> Generating...</> : "🎨 Generate Diagram"}
                                    </button>
                                </div>
                            )}

                            {/* Layout Engine */}
                            {rfNodes.length > 0 && (
                                <div className={styles.sectionDivided}>
                                    <label className={styles.fieldLabel}>Preview Layout Engine</label>
                                    <select className="input" value={renderEngine} onChange={(e) => setRenderEngine(e.target.value)}>
                                        <option value="dot">dot (hierarchical)</option>
                                        <option value="neato">neato (spring model)</option>
                                        <option value="fdp">fdp (force-directed)</option>
                                        <option value="circo">circo (circular)</option>
                                        <option value="twopi">twopi (radial)</option>
                                    </select>
                                </div>
                            )}

                            {/* Export */}
                            {rfNodes.length > 0 && (
                                <div className={styles.sectionDivided}>
                                    <label className={styles.fieldLabel}>Export (Graphviz quality)</label>
                                    <div className={styles.exportButtons}>
                                        <button className="btn btn-secondary" onClick={() => handleExport("svg")}>📄 SVG</button>
                                        <button className="btn btn-secondary" onClick={() => handleExport("png")}>🖼 PNG</button>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* RIGHT — MAIN AREA */}
                <div className={styles.editorPane}>
                    {/* Tab Bar */}
                    <div className={styles.editorToolbar}>
                        <div className={styles.tabGroup}>
                            <button className={`${styles.editorTab} ${viewTab === "editor" ? styles.editorTabActive : ""}`} onClick={() => setViewTab("editor")}>
                                ✏️ Interactive Editor
                            </button>
                            <button
                                className={`${styles.editorTab} ${viewTab === "preview" ? styles.editorTabActive : ""}`}
                                onClick={handlePreview}
                                disabled={rfNodes.length === 0}
                            >
                                📐 Graphviz Preview
                            </button>
                        </div>

                        <div className={styles.toolbarActions}>
                            {viewTab === "editor" && (
                                <>
                                    <button className={styles.toolBtn} onClick={handleAutoLayout} title="Rearrange nodes hierarchically">
                                        <span className={styles.toolIcon}>🔀</span> Auto Layout
                                    </button>
                                    <button className={styles.toolBtn} onClick={handleAddNode}>
                                        <span className={styles.toolIcon}>＋</span> Add Node
                                    </button>
                                    <button className={styles.toolBtn} onClick={handleDeleteSelected}>
                                        <span className={styles.toolIcon}>🗑</span> Delete Selected
                                    </button>
                                    <button className={styles.toolBtn} onClick={() => fitView({ padding: 0.2, duration: 300 })}>
                                        <span className={styles.toolIcon}>⊞</span> Fit View
                                    </button>
                                </>
                            )}
                        </div>
                    </div>

                    {/* Canvas Area */}
                    <div className={styles.canvasArea}>
                        {loading && (
                            <div className={styles.canvasOverlay}>
                                <div className={styles.spinner} />
                                <p>AI is generating your diagram...</p>
                            </div>
                        )}

                        {/* EDITOR TAB */}
                        {viewTab === "editor" && (
                            <div className={styles.reactFlowWrap}>
                                <ReactFlow
                                    nodes={rfNodes}
                                    edges={rfEdges}
                                    onNodesChange={onNodesChange}
                                    onEdgesChange={onEdgesChange}
                                    onConnect={onConnect}
                                    onDoubleClick={onPaneDoubleClick}
                                    nodeTypes={nodeTypes}
                                    fitView
                                    snapToGrid
                                    snapGrid={[16, 16]}
                                    deleteKeyCode="Delete"
                                    multiSelectionKeyCode="Shift"
                                    style={{ width: "100%", height: "100%" }}
                                    defaultEdgeOptions={{
                                        animated: true,
                                        style: { stroke: "#2c6a73", strokeWidth: 2 },
                                        markerEnd: { type: MarkerType.ArrowClosed, color: "#2c6a73", width: 16, height: 16 },
                                    }}
                                >
                                    <Controls
                                        position="bottom-right"
                                        style={{ borderRadius: "8px", border: "1px solid #e5e7eb", boxShadow: "0 2px 8px rgba(0,0,0,0.06)" }}
                                    />
                                    <MiniMap
                                        nodeColor={(n) => (n.data?.color as string) || "#e8f4f6"}
                                        maskColor="rgba(248, 249, 251, 0.7)"
                                        style={{ border: "1px solid #e5e7eb", borderRadius: "8px" }}
                                        position="bottom-left"
                                    />
                                    <Background variant={BackgroundVariant.Dots} gap={16} size={1} color="#ddd" />

                                    {/* Instructional overlay when empty */}
                                    {rfNodes.length === 0 && !loading && (
                                        <Panel position="top-center">
                                            <div className={styles.emptyPanel}>
                                                <div className={styles.emptyIcon}>🎨</div>
                                                <h3>Start Building Your Diagram</h3>
                                                <p>Use the sidebar to generate from text/code, or build manually:</p>
                                                <div className={styles.instructions}>
                                                    <div className={styles.instruction}><span>＋</span> Click <b>"Add Node"</b> or <b>double-click canvas</b></div>
                                                    <div className={styles.instruction}><span>🔗</span> Drag from a node handle to connect</div>
                                                    <div className={styles.instruction}><span>✏️</span> Double-click a node to edit its label</div>
                                                    <div className={styles.instruction}><span>🗑</span> Hover a node for the delete button</div>
                                                    <div className={styles.instruction}><span>📐</span> Click <b>"Graphviz Preview"</b> for publication-ready output</div>
                                                </div>
                                            </div>
                                        </Panel>
                                    )}
                                </ReactFlow>
                            </div>
                        )}

                        {/* PREVIEW TAB */}
                        {viewTab === "preview" && (
                            <div className={styles.previewWrap}>
                                {previewSvg ? (
                                    <TransformWrapper
                                        initialScale={1}
                                        minScale={0.1}
                                        maxScale={4}
                                        centerOnInit
                                        wheel={{ step: 0.1 }}
                                    >
                                        {({ zoomIn, zoomOut, resetTransform }) => (
                                            <>
                                                <div className={styles.zoomControls}>
                                                    <button onClick={() => zoomIn()} className={styles.zoomBtn} title="Zoom in">+</button>
                                                    <button onClick={() => zoomOut()} className={styles.zoomBtn} title="Zoom out">−</button>
                                                    <button onClick={() => resetTransform()} className={styles.zoomBtn} title="Reset view">⊞</button>
                                                </div>
                                                <TransformComponent
                                                    wrapperStyle={{ width: "100%", height: "100%" }}
                                                    contentStyle={{ width: "100%", height: "100%", display: "flex", justifyContent: "center", alignItems: "center" }}
                                                >
                                                    <div
                                                        className={styles.previewSvgContainer}
                                                        dangerouslySetInnerHTML={{ __html: previewSvg }}
                                                    />
                                                </TransformComponent>
                                            </>
                                        )}
                                    </TransformWrapper>
                                ) : (
                                    <div className={styles.emptyPanel}>
                                        <p>Build a diagram in the editor, then click "Graphviz Preview" to see the publication-ready render.</p>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

export default function VisualizePage() {
    return (
        <ReactFlowProvider>
            <VisualizationStudioInner />
        </ReactFlowProvider>
    );
}
