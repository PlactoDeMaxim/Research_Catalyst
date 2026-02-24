"use client";

import { useState, useCallback } from "react";
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

const API_BASE = "http://localhost:8000/api/papers";

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

    const [results, setResults] = useState<SearchResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSearch = useCallback(
        async (e: React.FormEvent) => {
            e.preventDefault();
            if (!query.trim()) return;

            setLoading(true);
            setError(null);
            setResults(null);
            setSelectedPaper(null);

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
