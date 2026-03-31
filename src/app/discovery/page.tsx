"use client";

import { useState, useCallback, useMemo } from "react";
import styles from "./page.module.css";

/* ── Types matching the backend Paper model ── */
interface Paper {
    id: string;
    title: string;
    abstract: string;
    authors: string[];
    year: number;
    venue: string;
    doi: string | null;
    arxiv_id: string | null;
    source: string;
    url: string;
    pdf_url: string | null;
    citation_count: number | null;
    open_access: boolean;
}

interface SearchResponse {
    papers: Paper[];
    total_results: number;
    sources_used: string[];
}

interface EvidenceSnippet {
    paper_id: string;
    title: string;
    source: string;
    excerpt: string;
    score: number;
}

interface WorkspaceChatResponse {
    answer: string;
    evidence: EvidenceSnippet[];
    project_id?: string | null;
}

interface ThemeItem {
    label: string;
    count: number;
    supporting_papers: string[];
}

interface LiteratureSynthesisResponse {
    summary: string;
    themes: ThemeItem[];
    notable_papers: string[];
    gaps: string[];
    project_id?: string | null;
}

interface ExtractionTableResponse {
    columns: string[];
    rows: Record<string, string>[];
}

interface GapAnalysisResponse {
    common_themes: string[];
    underexplored_topics: string[];
    contradiction_signals: string[];
    project_id?: string | null;
}

const API_BASE = "http://localhost:8000/api/papers";
const SUMMARY_API_BASE = "http://localhost:8000/api/summary/workspace";

const SOURCE_LABELS: Record<string, string> = {
    openalex: "OpenAlex",
    arxiv: "arXiv",
    crossref: "Crossref",
    semantic_scholar: "Semantic Scholar",
};

const SOURCE_COLORS: Record<string, string> = {
    openalex: "#2c6a73",
    arxiv: "#b31b1b",
    crossref: "#1a5276",
    semantic_scholar: "#1857b6",
};

export default function DiscoveryPage() {
    const [query, setQuery] = useState("");
    const [yearFrom, setYearFrom] = useState("");
    const [yearTo, setYearTo] = useState("");
    const [openAccessOnly, setOpenAccessOnly] = useState(false);
    const [limit, setLimit] = useState("20");
    const [selectedPaper, setSelectedPaper] = useState<string | null>(null);
    const [selectedPaperIds, setSelectedPaperIds] = useState<string[]>([]);
    const [workspaceQuestion, setWorkspaceQuestion] = useState("");
    const [workspaceFocus, setWorkspaceFocus] = useState("");
    const [workspaceLoading, setWorkspaceLoading] = useState(false);
    const [workspaceError, setWorkspaceError] = useState<string | null>(null);
    const [chatResult, setChatResult] = useState<WorkspaceChatResponse | null>(null);
    const [synthesisResult, setSynthesisResult] = useState<LiteratureSynthesisResponse | null>(null);
    const [tableResult, setTableResult] = useState<ExtractionTableResponse | null>(null);
    const [gapResult, setGapResult] = useState<GapAnalysisResponse | null>(null);

    const [results, setResults] = useState<SearchResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const selectedPapers = useMemo(
        () => results?.papers.filter((paper) => selectedPaperIds.includes(paper.id)) ?? [],
        [results, selectedPaperIds]
    );

    const handleSearch = useCallback(
        async (e: React.FormEvent) => {
            e.preventDefault();
            if (!query.trim()) return;

            setLoading(true);
            setError(null);
            setResults(null);
            setSelectedPaper(null);
            setSelectedPaperIds([]);
            setChatResult(null);
            setSynthesisResult(null);
            setTableResult(null);
            setGapResult(null);
            setWorkspaceError(null);

            try {
                const params = new URLSearchParams({ query: query.trim() });
                if (yearFrom) params.set("year_from", yearFrom);
                if (yearTo) params.set("year_to", yearTo);
                if (openAccessOnly) params.set("open_access_only", "true");
                if (limit) params.set("limit", limit);

                const resp = await fetch(`${API_BASE}/search?${params}`);
                if (!resp.ok) {
                    throw new Error(`Server error: ${resp.status}`);
                }
                const data: SearchResponse = await resp.json();
                setResults(data);
            } catch (err: unknown) {
                const msg = err instanceof Error ? err.message : "Search failed";
                setError(msg);
            } finally {
                setLoading(false);
            }
        },
        [query, yearFrom, yearTo, openAccessOnly, limit]
    );

    const togglePaperSelection = useCallback((paperId: string) => {
        setSelectedPaperIds((prev) =>
            prev.includes(paperId) ? prev.filter((id) => id !== paperId) : [...prev, paperId]
        );
    }, []);

    const runWorkspaceRequest = useCallback(
        async (path: string, payload: Record<string, unknown>) => {
            if (selectedPapers.length === 0) {
                setWorkspaceError("Select at least one paper first.");
                return null;
            }
            setWorkspaceLoading(true);
            setWorkspaceError(null);
            try {
                const resp = await fetch(`${SUMMARY_API_BASE}${path}`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ papers: selectedPapers, ...payload }),
                });
                if (!resp.ok) {
                    throw new Error(`Workspace request failed: ${resp.status}`);
                }
                return await resp.json();
            } catch (err: unknown) {
                const msg = err instanceof Error ? err.message : "Workspace action failed";
                setWorkspaceError(msg);
                return null;
            } finally {
                setWorkspaceLoading(false);
            }
        },
        [selectedPapers]
    );

    const handleWorkspaceChat = useCallback(async () => {
        if (!workspaceQuestion.trim()) {
            setWorkspaceError("Enter a question for the selected papers.");
            return;
        }
        const data = (await runWorkspaceRequest("/chat", {
            question: workspaceQuestion.trim(),
        })) as WorkspaceChatResponse | null;
        if (data) setChatResult(data);
    }, [runWorkspaceRequest, workspaceQuestion]);

    const handleSynthesis = useCallback(async () => {
        const data = (await runWorkspaceRequest("/synthesize", {
            focus: workspaceFocus.trim(),
        })) as LiteratureSynthesisResponse | null;
        if (data) setSynthesisResult(data);
    }, [runWorkspaceRequest, workspaceFocus]);

    const handleExtractTable = useCallback(async () => {
        const data = (await runWorkspaceRequest("/extract-table", {})) as ExtractionTableResponse | null;
        if (data) setTableResult(data);
    }, [runWorkspaceRequest]);

    const handleGapAnalysis = useCallback(async () => {
        const data = (await runWorkspaceRequest("/gap-analysis", {
            topic: workspaceFocus.trim() || query.trim(),
        })) as GapAnalysisResponse | null;
        if (data) setGapResult(data);
    }, [runWorkspaceRequest, workspaceFocus, query]);

    const handleSaveCollection = useCallback(async () => {
        if (selectedPapers.length === 0) {
            setWorkspaceError("Select at least one paper first.");
            return;
        }
        const title = window.prompt("Collection title", workspaceFocus.trim() || query.trim() || "Saved Literature Set");
        if (!title?.trim()) return;
        const tagsRaw = window.prompt("Optional tags (comma-separated)", workspaceFocus.trim());
        const resp = await fetch(`${SUMMARY_API_BASE}/collections`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                title: title.trim(),
                description: `Saved from discovery query: ${query.trim()}`,
                tags: (tagsRaw || "")
                    .split(",")
                    .map((item) => item.trim())
                    .filter(Boolean),
                papers: selectedPapers,
            }),
        });
        if (!resp.ok) {
            setWorkspaceError(`Failed to save collection: ${resp.status}`);
            return;
        }
        setWorkspaceError(null);
    }, [selectedPapers, workspaceFocus, query]);

    const handleCreateScreening = useCallback(async () => {
        if (selectedPapers.length === 0) {
            setWorkspaceError("Select papers before creating a screening session.");
            return;
        }
        const title = window.prompt("Screening session title", `Screening: ${query.trim() || "Selected Papers"}`);
        if (!title?.trim()) return;
        const inclusion = window.prompt("Inclusion criteria", workspaceFocus.trim() || query.trim());
        const exclusion = window.prompt("Exclusion criteria", "");
        const resp = await fetch(`${SUMMARY_API_BASE}/screening-sessions`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                title: title.trim(),
                query: query.trim(),
                inclusion_criteria: inclusion || "",
                exclusion_criteria: exclusion || "",
            }),
        });
        if (!resp.ok) {
            setWorkspaceError(`Failed to create screening session: ${resp.status}`);
            return;
        }
        const session: { id: string } = await resp.json();
        await Promise.all(
            selectedPapers.map((paper) =>
                fetch(`${SUMMARY_API_BASE}/screening-sessions/${session.id}/entries`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        paper,
                        decision: "maybe",
                        reason: "Imported from discovery selection.",
                        tags: [],
                    }),
                })
            )
        );
        setWorkspaceError(null);
    }, [selectedPapers, workspaceFocus, query]);

    return (
        <div>
            <div className="page-header animate-in">
                <h1>Paper Discovery</h1>
                <p>
                    Search across OpenAlex, arXiv, Crossref &amp; Semantic Scholar — results
                    are deduplicated, ranked, and cached.
                </p>
            </div>

            {/* ── Search Form ── */}
            <form onSubmit={handleSearch} className={`${styles.searchBox} animate-in`}>
                <div className={styles.searchIcon}>🔍</div>
                <input
                    type="text"
                    className={styles.searchInput}
                    placeholder="Describe your research problem or topic..."
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                />
                <button type="submit" className="btn btn-primary" disabled={loading}>
                    {loading ? "Searching…" : "Search"}
                </button>
            </form>

            {/* ── Filters ── */}
            <div className={`${styles.filters} animate-in`}>
                <div className={styles.filterGroup}>
                    <label className={styles.filterLabel}>Year from</label>
                    <input
                        type="number"
                        className={styles.filterInput}
                        placeholder="e.g. 2018"
                        value={yearFrom}
                        onChange={(e) => setYearFrom(e.target.value)}
                        min="1900"
                        max="2099"
                    />
                </div>
                <div className={styles.filterGroup}>
                    <label className={styles.filterLabel}>Year to</label>
                    <input
                        type="number"
                        className={styles.filterInput}
                        placeholder="e.g. 2025"
                        value={yearTo}
                        onChange={(e) => setYearTo(e.target.value)}
                        min="1900"
                        max="2099"
                    />
                </div>
                <div className={styles.filterGroup}>
                    <label className={styles.filterLabel}>Limit</label>
                    <select
                        className={styles.filterInput}
                        value={limit}
                        onChange={(e) => setLimit(e.target.value)}
                    >
                        <option value="10">10</option>
                        <option value="20">20</option>
                        <option value="50">50</option>
                        <option value="100">100</option>
                    </select>
                </div>
                <div className={styles.filterGroup}>
                    <label className={styles.filterLabel}>&nbsp;</label>
                    <button
                        type="button"
                        className={`${styles.filterChip} ${openAccessOnly ? styles.filterActive : ""}`}
                        onClick={() => setOpenAccessOnly(!openAccessOnly)}
                    >
                        🔓 Open Access Only
                    </button>
                </div>
            </div>

            {/* ── Loading ── */}
            {loading && (
                <div className={styles.loadingState}>
                    <div className={styles.spinner} />
                    <p>Searching across multiple academic databases…</p>
                </div>
            )}

            {/* ── Error ── */}
            {error && (
                <div className={styles.errorState}>
                    <span className={styles.errorIcon}>⚠️</span>
                    <p>{error}</p>
                    <button className="btn btn-secondary" onClick={() => setError(null)}>
                        Dismiss
                    </button>
                </div>
            )}

            {/* ── Results ── */}
            {results && results.papers.length > 0 && (
                <div className={styles.results}>
                    <div className={styles.resultsMeta}>
                        <span>
                            <strong>{results.total_results}</strong> papers found
                            {results.papers.length < results.total_results &&
                                ` (showing top ${results.papers.length})`}
                        </span>
                        <span className={styles.sourcesUsed}>
                            Sources:{" "}
                            {results.sources_used.map((s) => SOURCE_LABELS[s] || s).join(", ")}
                        </span>
                    </div>

                    <div className={`${styles.workspaceBox} card`}>
                        <div className={styles.workspaceHeader}>
                            <div>
                                <h3 className={styles.workspaceTitle}>Phase 2 Literature Workspace</h3>
                                <p className={styles.workspaceSubtitle}>
                                    {selectedPapers.length} selected paper{selectedPapers.length === 1 ? "" : "s"} ready for chat, synthesis, extraction, gap analysis, collections, and screening.
                                </p>
                            </div>
                            <div className={styles.workspaceSelectionActions}>
                                <button
                                    className="btn btn-ghost"
                                    onClick={() => setSelectedPaperIds(results.papers.map((paper) => paper.id))}
                                >
                                    Select all
                                </button>
                                <button className="btn btn-ghost" onClick={() => setSelectedPaperIds([])}>
                                    Clear
                                </button>
                            </div>
                        </div>

                        <div className={styles.workspaceControls}>
                            <input
                                className={styles.workspaceInput}
                                placeholder="Ask a question across selected papers..."
                                value={workspaceQuestion}
                                onChange={(e) => setWorkspaceQuestion(e.target.value)}
                            />
                            <input
                                className={styles.workspaceInput}
                                placeholder="Optional focus or theme (e.g. RAG, benchmark design)"
                                value={workspaceFocus}
                                onChange={(e) => setWorkspaceFocus(e.target.value)}
                            />
                        </div>

                        <div className={styles.workspaceActions}>
                            <button className="btn btn-primary" onClick={() => void handleWorkspaceChat()} disabled={workspaceLoading}>
                                {workspaceLoading ? "Working..." : "Chat"}
                            </button>
                            <button className="btn btn-secondary" onClick={() => void handleSynthesis()} disabled={workspaceLoading}>
                                Synthesize
                            </button>
                            <button className="btn btn-secondary" onClick={() => void handleExtractTable()} disabled={workspaceLoading}>
                                Extract Table
                            </button>
                            <button className="btn btn-secondary" onClick={() => void handleGapAnalysis()} disabled={workspaceLoading}>
                                Gap Analysis
                            </button>
                            <button className="btn btn-ghost" onClick={() => void handleSaveCollection()} disabled={workspaceLoading}>
                                Save Collection
                            </button>
                            <button className="btn btn-ghost" onClick={() => void handleCreateScreening()} disabled={workspaceLoading}>
                                Start Screening
                            </button>
                        </div>

                        {workspaceError && <div className={styles.workspaceError}>{workspaceError}</div>}

                        {(chatResult || synthesisResult || tableResult || gapResult) && (
                            <div className={styles.workspaceOutputs}>
                                {chatResult && (
                                    <div className={styles.workspacePanel}>
                                        <h4>Chat Answer</h4>
                                        <p>{chatResult.answer}</p>
                                        {chatResult.evidence.length > 0 && (
                                            <div className={styles.workspaceEvidenceList}>
                                                {chatResult.evidence.map((item) => (
                                                    <div key={`${item.paper_id}-${item.source}`} className={styles.workspaceEvidenceItem}>
                                                        <strong>{item.title}</strong>
                                                        <span>{item.source} · score {item.score.toFixed(2)}</span>
                                                        <p>{item.excerpt}</p>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                )}

                                {synthesisResult && (
                                    <div className={styles.workspacePanel}>
                                        <h4>Literature Synthesis</h4>
                                        <p>{synthesisResult.summary}</p>
                                        {synthesisResult.themes.length > 0 && (
                                            <div className={styles.workspaceTagList}>
                                                {synthesisResult.themes.map((theme) => (
                                                    <span key={theme.label} className={styles.workspaceTag}>
                                                        {theme.label} ({theme.count})
                                                    </span>
                                                ))}
                                            </div>
                                        )}
                                        {synthesisResult.gaps.length > 0 && (
                                            <ul className={styles.workspaceList}>
                                                {synthesisResult.gaps.map((gap) => (
                                                    <li key={gap}>{gap}</li>
                                                ))}
                                            </ul>
                                        )}
                                    </div>
                                )}

                                {tableResult && (
                                    <div className={styles.workspacePanel}>
                                        <h4>Extraction Table</h4>
                                        <div className={styles.workspaceTableWrap}>
                                            <table className={styles.workspaceTable}>
                                                <thead>
                                                    <tr>
                                                        {tableResult.columns.map((column) => (
                                                            <th key={column}>{column}</th>
                                                        ))}
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {tableResult.rows.map((row, index) => (
                                                        <tr key={`${row.title}-${index}`}>
                                                            {tableResult.columns.map((column) => (
                                                                <td key={column}>{row[column] ?? ""}</td>
                                                            ))}
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                )}

                                {gapResult && (
                                    <div className={styles.workspacePanel}>
                                        <h4>Gap Analysis</h4>
                                        <p><strong>Common themes:</strong> {gapResult.common_themes.join(", ") || "No strong common themes detected."}</p>
                                        <p><strong>Underexplored:</strong> {gapResult.underexplored_topics.join(", ") || "No obvious weak spots detected."}</p>
                                        {gapResult.contradiction_signals.length > 0 && (
                                            <ul className={styles.workspaceList}>
                                                {gapResult.contradiction_signals.map((item) => (
                                                    <li key={item}>{item}</li>
                                                ))}
                                            </ul>
                                        )}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                    <div className={styles.resultsList}>
                        {results.papers.map((paper) => (
                            <div
                                key={paper.id}
                                className={`card ${styles.paperCard} animate-in ${selectedPaper === paper.id ? styles.paperSelected : ""
                                    }`}
                                onClick={() =>
                                    setSelectedPaper(
                                        paper.id === selectedPaper ? null : paper.id
                                    )
                                }
                            >
                                <div className={styles.paperHeader}>
                                    <div className={styles.paperBadges}>
                                        <label
                                            className={styles.selectBadge}
                                            onClick={(e) => e.stopPropagation()}
                                        >
                                            <input
                                                type="checkbox"
                                                checked={selectedPaperIds.includes(paper.id)}
                                                onChange={() => togglePaperSelection(paper.id)}
                                            />
                                            Select
                                        </label>
                                        <span
                                            className={styles.sourceBadge}
                                            style={{
                                                background: `${SOURCE_COLORS[paper.source] || "#5e6472"}15`,
                                                color: SOURCE_COLORS[paper.source] || "#5e6472",
                                                borderColor: `${SOURCE_COLORS[paper.source] || "#5e6472"}30`,
                                            }}
                                        >
                                            {SOURCE_LABELS[paper.source] || paper.source}
                                        </span>
                                        {paper.open_access && (
                                            <span className={styles.oaBadge}>🔓 Open Access</span>
                                        )}
                                    </div>
                                    <div className={styles.paperMeta}>
                                        {paper.year > 0 && <span>{paper.year}</span>}
                                        {paper.citation_count != null && (
                                            <>
                                                <span>•</span>
                                                <span>
                                                    {paper.citation_count.toLocaleString()} citations
                                                </span>
                                            </>
                                        )}
                                    </div>
                                </div>

                                <h3 className={styles.paperTitle}>{paper.title}</h3>

                                <p className={styles.paperAuthors}>
                                    {paper.authors.slice(0, 5).join(", ")}
                                    {paper.authors.length > 5 && ` + ${paper.authors.length - 5} more`}
                                </p>

                                {paper.venue && (
                                    <p className={styles.paperVenue}>
                                        📖 {paper.venue}
                                    </p>
                                )}

                                {paper.abstract && (
                                    <p className={styles.paperAbstract}>{paper.abstract}</p>
                                )}

                                {selectedPaper === paper.id && (
                                    <div className={styles.paperActions}>
                                        {paper.url && (
                                            <a
                                                href={paper.url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="btn btn-primary"
                                                style={{ fontSize: "0.8rem" }}
                                                onClick={(e) => e.stopPropagation()}
                                            >
                                                🔗 View Paper
                                            </a>
                                        )}
                                        {paper.pdf_url && (
                                            <a
                                                href={paper.pdf_url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="btn btn-secondary"
                                                style={{ fontSize: "0.8rem" }}
                                                onClick={(e) => e.stopPropagation()}
                                            >
                                                📄 PDF
                                            </a>
                                        )}
                                        {paper.doi && (
                                            <a
                                                href={`https://doi.org/${paper.doi}`}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="btn btn-ghost"
                                                style={{ fontSize: "0.8rem" }}
                                                onClick={(e) => e.stopPropagation()}
                                            >
                                                DOI: {paper.doi}
                                            </a>
                                        )}
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* ── No results ── */}
            {results && results.papers.length === 0 && !loading && (
                <div className="empty-state animate-in">
                    <div className="empty-state-icon">🔍</div>
                    <h3>No Papers Found</h3>
                    <p>Try broadening your search terms or adjusting the filters.</p>
                </div>
            )}

            {/* ── Initial empty state ── */}
            {!results && !loading && !error && (
                <div className="empty-state animate-in">
                    <div className="empty-state-icon">🧭</div>
                    <h3>Start Your Discovery</h3>
                    <p>
                        Enter a research problem statement above to find relevant papers across
                        multiple academic databases.
                    </p>
                </div>
            )}
        </div>
    );
}
