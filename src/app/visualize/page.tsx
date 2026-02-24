"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import styles from "./page.module.css";
import {
    ReactFlow,
    MiniMap,
    Controls,
    Background,
    addEdge,
    useNodesState,
    useEdgesState,
    type Node,
    type Edge,
    type Connection,
    BackgroundVariant,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

const API_BASE = "http://localhost:8000/api/visualization";

/* ── Types ── */
type ActiveMode = "diagram" | "chart";
type DiagramFormat = "graphviz" | "mermaid";
type ChartType = "line" | "bar" | "scatter";

/* ── Mermaid Renderer Component ── */
function MermaidRenderer({ definition }: { definition: string }) {
    const containerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!containerRef.current || !definition) return;
        let cancelled = false;

        (async () => {
            const mermaid = (await import("mermaid")).default;
            mermaid.initialize({
                startOnLoad: false,
                theme: "default",
                fontFamily: "Inter, sans-serif",
            });
            if (cancelled) return;
            try {
                const { svg } = await mermaid.render(
                    `mermaid-${Date.now()}`,
                    definition
                );
                if (!cancelled && containerRef.current) {
                    containerRef.current.innerHTML = svg;
                }
            } catch (err) {
                if (!cancelled && containerRef.current) {
                    containerRef.current.innerHTML = `<p style="color:#b91c1c">Mermaid render error: ${err}</p>`;
                }
            }
        })();

        return () => { cancelled = true; };
    }, [definition]);

    return <div ref={containerRef} className={styles.mermaidContainer} />;
}

/* ── Main Page ── */
export default function VisualizePage() {
    // Mode
    const [activeMode, setActiveMode] = useState<ActiveMode>("diagram");

    // Diagram state
    const [diagramFormat, setDiagramFormat] = useState<DiagramFormat>("graphviz");
    const [nodesInput, setNodesInput] = useState("Problem\nLiterature Review\nMethodology\nResults\nConclusion");
    const [edgesInput, setEdgesInput] = useState("Problem,Literature Review\nLiterature Review,Methodology\nMethodology,Results\nResults,Conclusion");
    const [diagramTitle, setDiagramTitle] = useState("Research Pipeline");
    const [diagramDef, setDiagramDef] = useState("");
    const [svgContent, setSvgContent] = useState("");

    // Chart state
    const [chartType, setChartType] = useState<ChartType>("line");
    const [chartTitle, setChartTitle] = useState("Training Accuracy");
    const [chartXLabel, setChartXLabel] = useState("Epoch");
    const [chartYLabel, setChartYLabel] = useState("Accuracy");
    const [chartData, setChartData] = useState('[\n  {"x": [1,2,3,4,5], "y": [0.65,0.72,0.81,0.87,0.91], "label": "Model A"},\n  {"x": [1,2,3,4,5], "y": [0.60,0.68,0.75,0.82,0.88], "label": "Model B"}\n]');
    const [chartSvg, setChartSvg] = useState("");

    // React Flow state
    const [rfNodes, setRfNodes, onNodesChange] = useNodesState<Node>([]);
    const [rfEdges, setRfEdges, onEdgesChange] = useEdgesState<Edge>([]);
    const onConnect = useCallback(
        (params: Connection) => setRfEdges((eds) => addEdge(params, eds)),
        [setRfEdges]
    );

    // Loading / error
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    /* ── Generate diagram ── */
    const handleGenerateDiagram = useCallback(async () => {
        setLoading(true);
        setError(null);
        setSvgContent("");
        setDiagramDef("");

        try {
            const nodes = nodesInput.split("\n").map((n) => n.trim()).filter(Boolean);
            const edges = edgesInput.split("\n").map((e) => e.split(",").map((s) => s.trim())).filter((e) => e.length >= 2);

            // Step 1: Generate definition
            const genResp = await fetch(`${API_BASE}/diagram/generate`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    type: "flowchart",
                    nodes,
                    edges,
                    format: diagramFormat,
                    title: diagramTitle,
                }),
            });
            if (!genResp.ok) throw new Error(`Generation failed: ${genResp.status}`);
            const genData = await genResp.json();
            setDiagramDef(genData.diagram_definition);

            // Step 2: If Graphviz, render to SVG on backend
            if (diagramFormat === "graphviz") {
                const renderResp = await fetch(`${API_BASE}/diagram/render`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        definition: genData.diagram_definition,
                        format: "graphviz",
                    }),
                });
                if (!renderResp.ok) throw new Error(`Render failed: ${renderResp.status}`);
                const renderData = await renderResp.json();
                setSvgContent(renderData.svg);
            }
            // Mermaid: definition stored, rendered by MermaidRenderer component

            // Step 3: Populate React Flow editor
            const flowNodes: Node[] = nodes.map((label, i) => ({
                id: `node-${i}`,
                data: { label },
                position: { x: 150, y: i * 100 + 30 },
                style: {
                    background: "#e8f4f6",
                    border: "1px solid #2c6a73",
                    borderRadius: "8px",
                    padding: "8px 16px",
                    fontSize: "13px",
                    fontFamily: "Inter, sans-serif",
                },
            }));
            const flowEdges: Edge[] = edges.map((e, i) => {
                const srcIdx = nodes.indexOf(e[0]);
                const tgtIdx = nodes.indexOf(e[1]);
                return {
                    id: `edge-${i}`,
                    source: `node-${srcIdx >= 0 ? srcIdx : 0}`,
                    target: `node-${tgtIdx >= 0 ? tgtIdx : 0}`,
                    animated: true,
                    style: { stroke: "#2c6a73" },
                };
            });
            setRfNodes(flowNodes);
            setRfEdges(flowEdges);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Diagram generation failed");
        } finally {
            setLoading(false);
        }
    }, [nodesInput, edgesInput, diagramFormat, diagramTitle, setRfNodes, setRfEdges]);

    /* ── Generate chart ── */
    const handleGenerateChart = useCallback(async () => {
        setLoading(true);
        setError(null);
        setChartSvg("");

        try {
            const data = JSON.parse(chartData);
            const resp = await fetch(`${API_BASE}/chart/generate`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    chart_type: chartType,
                    data,
                    title: chartTitle,
                    x_label: chartXLabel,
                    y_label: chartYLabel,
                }),
            });
            if (!resp.ok) throw new Error(`Chart generation failed: ${resp.status}`);
            const result = await resp.json();
            setChartSvg(result.svg);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Chart generation failed");
        } finally {
            setLoading(false);
        }
    }, [chartData, chartType, chartTitle, chartXLabel, chartYLabel]);

    /* ── Export ── */
    const handleExport = useCallback(async (format: "svg" | "png" | "pdf") => {
        const content = activeMode === "chart" ? chartSvg : svgContent;
        if (!content) return;

        if (format === "svg") {
            const blob = new Blob([content], { type: "image/svg+xml" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `diagram.svg`;
            a.click();
            URL.revokeObjectURL(url);
            return;
        }

        try {
            const resp = await fetch(`${API_BASE}/export`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ svg_content: content, format }),
            });
            if (!resp.ok) throw new Error("Export failed");
            const blob = await resp.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `diagram.${format}`;
            a.click();
            URL.revokeObjectURL(url);
        } catch (err) {
            setError("Export failed");
        }
    }, [activeMode, chartSvg, svgContent]);

    const hasOutput = activeMode === "chart" ? !!chartSvg : !!(svgContent || (diagramFormat === "mermaid" && diagramDef));

    return (
        <div>
            <div className="page-header animate-in">
                <h1>Visualization Studio</h1>
                <p>Generate publication-ready diagrams, flowcharts, and charts from structured data.</p>
            </div>

            {/* ── Mode Tabs ── */}
            <div className={`${styles.tabs} animate-in`}>
                <button className={`${styles.tab} ${activeMode === "diagram" ? styles.tabActive : ""}`} onClick={() => setActiveMode("diagram")}>
                    🔀 Diagrams
                </button>
                <button className={`${styles.tab} ${activeMode === "chart" ? styles.tabActive : ""}`} onClick={() => setActiveMode("chart")}>
                    📊 Charts
                </button>
            </div>

            {error && (
                <div className={styles.errorBanner}>
                    ⚠️ {error}
                    <button className={styles.errorClose} onClick={() => setError(null)}>✕</button>
                </div>
            )}

            {/* ── Studio Layout ── */}
            <div className={styles.studioLayout}>
                {/* LEFT PANEL — Controls */}
                <div className={`card ${styles.controlPanel} animate-in`}>
                    <h3 className={styles.panelTitle}>Controls</h3>

                    {activeMode === "diagram" ? (
                        <>
                            <label className={styles.fieldLabel}>Format</label>
                            <select className="input" value={diagramFormat} onChange={(e) => setDiagramFormat(e.target.value as DiagramFormat)}>
                                <option value="graphviz">Graphviz (DOT)</option>
                                <option value="mermaid">Mermaid</option>
                            </select>

                            <label className={styles.fieldLabel}>Title</label>
                            <input className="input" value={diagramTitle} onChange={(e) => setDiagramTitle(e.target.value)} placeholder="Diagram title" />

                            <label className={styles.fieldLabel}>Nodes (one per line)</label>
                            <textarea className={`input ${styles.defTextarea}`} value={nodesInput} onChange={(e) => setNodesInput(e.target.value)} rows={5} />

                            <label className={styles.fieldLabel}>Edges (source,target per line)</label>
                            <textarea className={`input ${styles.defTextarea}`} value={edgesInput} onChange={(e) => setEdgesInput(e.target.value)} rows={5} />

                            <button className="btn btn-primary w-full" onClick={handleGenerateDiagram} disabled={loading} style={{ marginTop: "var(--space-md)" }}>
                                {loading ? "Generating…" : "🎨 Generate Diagram"}
                            </button>
                        </>
                    ) : (
                        <>
                            <label className={styles.fieldLabel}>Chart Type</label>
                            <select className="input" value={chartType} onChange={(e) => setChartType(e.target.value as ChartType)}>
                                <option value="line">Line Chart</option>
                                <option value="bar">Bar Chart</option>
                                <option value="scatter">Scatter Plot</option>
                            </select>

                            <label className={styles.fieldLabel}>Title</label>
                            <input className="input" value={chartTitle} onChange={(e) => setChartTitle(e.target.value)} />

                            <label className={styles.fieldLabel}>X Axis</label>
                            <input className="input" value={chartXLabel} onChange={(e) => setChartXLabel(e.target.value)} />

                            <label className={styles.fieldLabel}>Y Axis</label>
                            <input className="input" value={chartYLabel} onChange={(e) => setChartYLabel(e.target.value)} />

                            <label className={styles.fieldLabel}>Data (JSON)</label>
                            <textarea className={`input ${styles.defTextarea}`} value={chartData} onChange={(e) => setChartData(e.target.value)} rows={8} style={{ fontFamily: "var(--font-mono)", fontSize: "0.78rem" }} />

                            <button className="btn btn-primary w-full" onClick={handleGenerateChart} disabled={loading} style={{ marginTop: "var(--space-md)" }}>
                                {loading ? "Generating…" : "📊 Generate Chart"}
                            </button>
                        </>
                    )}

                    {/* Export Controls */}
                    {hasOutput && (
                        <div className={styles.exportControls}>
                            <h4 className={styles.fieldLabel}>Export</h4>
                            <div className={styles.exportButtons}>
                                <button className="btn btn-secondary" onClick={() => handleExport("svg")}>SVG</button>
                                <button className="btn btn-secondary" onClick={() => handleExport("png")}>PNG</button>
                                <button className="btn btn-secondary" onClick={() => handleExport("pdf")}>PDF</button>
                            </div>
                        </div>
                    )}
                </div>

                {/* CENTER PANEL — Viewer */}
                <div className={`card ${styles.viewerPanel} animate-in`}>
                    <h3 className={styles.panelTitle}>Preview</h3>
                    <div className={styles.viewerArea}>
                        {loading && (
                            <div className={styles.loadingOverlay}>
                                <div className={styles.spinner} />
                                <p>Rendering…</p>
                            </div>
                        )}

                        {activeMode === "diagram" && svgContent && (
                            <div className={styles.svgContainer} dangerouslySetInnerHTML={{ __html: svgContent }} />
                        )}

                        {activeMode === "diagram" && diagramFormat === "mermaid" && diagramDef && !svgContent && (
                            <MermaidRenderer definition={diagramDef} />
                        )}

                        {activeMode === "chart" && chartSvg && (
                            <div className={styles.svgContainer} dangerouslySetInnerHTML={{ __html: chartSvg }} />
                        )}

                        {!hasOutput && !loading && (
                            <div className={styles.viewerPlaceholder}>
                                <span className={styles.placeholderIcon}>{activeMode === "chart" ? "📊" : "🔀"}</span>
                                <p>Your generated {activeMode === "chart" ? "chart" : "diagram"} will appear here</p>
                            </div>
                        )}
                    </div>

                    {/* Definition readout */}
                    {diagramDef && activeMode === "diagram" && (
                        <div className={styles.defReadout}>
                            <h4 className={styles.fieldLabel}>Generated Definition</h4>
                            <pre className={styles.defCode}>{diagramDef}</pre>
                        </div>
                    )}
                </div>

                {/* RIGHT PANEL — Editor */}
                <div className={`card ${styles.editorPanel} animate-in`}>
                    <h3 className={styles.panelTitle}>Interactive Editor</h3>
                    <div className={styles.editorArea}>
                        {rfNodes.length > 0 ? (
                            <ReactFlow
                                nodes={rfNodes}
                                edges={rfEdges}
                                onNodesChange={onNodesChange}
                                onEdgesChange={onEdgesChange}
                                onConnect={onConnect}
                                fitView
                                style={{ width: "100%", height: "100%" }}
                            >
                                <Controls />
                                <MiniMap
                                    nodeColor="#e8f4f6"
                                    maskColor="rgba(248, 249, 251, 0.7)"
                                    style={{ border: "1px solid #e5e7eb", borderRadius: "8px" }}
                                />
                                <Background variant={BackgroundVariant.Dots} gap={16} size={1} color="#ddd" />
                            </ReactFlow>
                        ) : (
                            <div className={styles.viewerPlaceholder}>
                                <span className={styles.placeholderIcon}>✏️</span>
                                <p>Generate a diagram to start editing interactively</p>
                                <span className={styles.placeholderHint}>
                                    Move nodes, add connections, edit labels
                                </span>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
