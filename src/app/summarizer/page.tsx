"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import styles from "./page.module.css";
import {
    getSummaryCategories,
    getSummaryPapers,
    getUploadedPapers,
    type SummaryPaperCard,
    type SummaryPaperDetail,
} from "./_components/summaryApi";
import UploadModal from "./_components/UploadModal";

const PAGE_SIZE = 6;

function stableHash(input: string) {
    let h = 0;
    for (let i = 0; i < input.length; i++) h = (h * 31 + input.charCodeAt(i)) | 0;
    return Math.abs(h);
}

function colorForCategory(category: string) {
    const palette = [
        "#2c6a73",
        "#429fad",
        "#1857b6",
        "#1a5276",
        "#e8856e",
        "#c49a2a",
        "#b31b1b",
        "#2f7d32",
        "#6f42c1",
        "#0b7285",
    ];
    const idx = stableHash(category) % palette.length;
    return palette[idx];
}

function safeTrimAuthors(authors: string[], max = 3) {
    const list = (authors ?? []).filter(Boolean);
    return list.slice(0, max).join(", ") + (list.length > max ? ` +${list.length - max}` : "");
}

function getSavedSlugs(): Set<string> {
    try {
        const raw = localStorage.getItem("savedSummaryPapers");
        if (!raw) return new Set();
        const arr = JSON.parse(raw) as string[];
        return new Set(arr);
    } catch {
        return new Set();
    }
}

export default function SummaryPage() {
    const [categories, setCategories] = useState<string[]>([]);
    const [selectedCategory, setSelectedCategory] = useState<string>("All Papers");

    const [query, setQuery] = useState("");
    const [debouncedQuery, setDebouncedQuery] = useState("");

    const [latest, setLatest] = useState<SummaryPaperCard[]>([]);
    const [latestTotal, setLatestTotal] = useState(0);
    const [latestHasMore, setLatestHasMore] = useState(false);
    const [latestOffset, setLatestOffset] = useState(0);

    const [popular, setPopular] = useState<SummaryPaperCard[]>([]);
    const [popularTotal, setPopularTotal] = useState(0);
    const [popularHasMore, setPopularHasMore] = useState(false);
    const [popularOffset, setPopularOffset] = useState(0);

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [savedSlugs, setSavedSlugs] = useState<Set<string>>(new Set());
    const didLoadSavedRef = useRef(false);
    const router = useRouter();
    const searchParams = useSearchParams();

    const [uploadModalOpen, setUploadModalOpen] = useState(false);
    const [uploadedPapers, setUploadedPapers] = useState<SummaryPaperDetail[]>([]);

    useEffect(() => {
        if (didLoadSavedRef.current) return;
        didLoadSavedRef.current = true;
        setSavedSlugs(getSavedSlugs());
        // Load uploaded papers
        getUploadedPapers().then(setUploadedPapers).catch(() => {});
    }, []);

    const toggleSaved = useCallback((slug: string) => {
        setSavedSlugs((prev) => {
            const next = new Set(prev);
            if (next.has(slug)) next.delete(slug);
            else next.add(slug);
            try {
                localStorage.setItem("savedSummaryPapers", JSON.stringify(Array.from(next)));
            } catch {
                // ignore
            }
            return next;
        });
    }, []);

    useEffect(() => {
        const t = window.setTimeout(() => setDebouncedQuery(query), 350);
        return () => window.clearTimeout(t);
    }, [query]);

    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                const cats = await getSummaryCategories();
                if (cancelled) return;
                setCategories(cats);
                // Selected category may come from URL; we apply it in the next effect.
                setSelectedCategory("All Papers");
            } catch (err) {
                if (cancelled) return;
                setError(err instanceof Error ? err.message : "Failed to load categories");
            }
        })();
        return () => {
            cancelled = true;
        };
    }, []);

    const loadInitial = useCallback(async () => {
        setError(null);
        setLoading(true);

        const categoryParam = selectedCategory === "All Papers" ? null : selectedCategory;

        try {
            const [latestResp, popularResp] = await Promise.all([
                getSummaryPapers({
                    mode: "latest",
                    limit: PAGE_SIZE,
                    offset: 0,
                    category: categoryParam,
                    q: debouncedQuery,
                }),
                getSummaryPapers({
                    mode: "popular",
                    limit: PAGE_SIZE,
                    offset: 0,
                    category: categoryParam,
                    q: debouncedQuery,
                }),
            ]);

            setLatest(latestResp.data);
            setLatestTotal(latestResp.total);
            setLatestHasMore(latestResp.hasMore);
            setLatestOffset(0);

            setPopular(popularResp.data);
            setPopularTotal(popularResp.total);
            setPopularHasMore(popularResp.hasMore);
            setPopularOffset(0);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to load papers");
        } finally {
            setLoading(false);
        }
    }, [debouncedQuery, selectedCategory]);

    useEffect(() => {
        if (!categories.length) return;
        void loadInitial();
    }, [categories.length, loadInitial]);

    // Apply category filter from URL (e.g. /summarizer?category=Language%20Models)
    useEffect(() => {
        const urlCategory = searchParams.get("category");
        if (!categories.length) return;

        if (!urlCategory || urlCategory === "All Papers") {
            setSelectedCategory("All Papers");
            return;
        }

        // Categories come from the backend; match exact names.
        if (categories.includes(urlCategory)) {
            setSelectedCategory(urlCategory);
        } else {
            setSelectedCategory("All Papers");
        }
    }, [categories, searchParams]);

    const loadMoreLatest = useCallback(async () => {
        if (!latestHasMore || loading) return;
        const categoryParam = selectedCategory === "All Papers" ? null : selectedCategory;
        const nextOffset = latestOffset + PAGE_SIZE;
        setLoading(true);
        try {
            const resp = await getSummaryPapers({
                mode: "latest",
                limit: PAGE_SIZE,
                offset: nextOffset,
                category: categoryParam,
                q: debouncedQuery,
            });
            setLatest((prev) => [...prev, ...resp.data]);
            setLatestTotal(resp.total);
            setLatestHasMore(resp.hasMore);
            setLatestOffset(nextOffset);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to load more latest papers");
        } finally {
            setLoading(false);
        }
    }, [debouncedQuery, latestHasMore, latestOffset, loading, selectedCategory]);

    const loadMorePopular = useCallback(async () => {
        if (!popularHasMore || loading) return;
        const categoryParam = selectedCategory === "All Papers" ? null : selectedCategory;
        const nextOffset = popularOffset + PAGE_SIZE;
        setLoading(true);
        try {
            const resp = await getSummaryPapers({
                mode: "popular",
                limit: PAGE_SIZE,
                offset: nextOffset,
                category: categoryParam,
                q: debouncedQuery,
            });
            setPopular((prev) => [...prev, ...resp.data]);
            setPopularTotal(resp.total);
            setPopularHasMore(resp.hasMore);
            setPopularOffset(nextOffset);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to load more popular papers");
        } finally {
            setLoading(false);
        }
    }, [debouncedQuery, loading, popularHasMore, popularOffset, selectedCategory]);

    const scrollToLatest = useCallback(() => {
        const el = document.getElementById("latest-research");
        el?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, []);

    const chipCategories = useMemo(() => ["All Papers", ...categories], [categories]);

    const onCategoryChipClick = useCallback(
        (cat: string) => {
            setSelectedCategory(cat);
            if (cat === "All Papers") {
                router.push("/summarizer", { scroll: false });
            } else {
                router.push(`/summarizer?category=${encodeURIComponent(cat)}`, { scroll: false });
            }
        },
        [router]
    );

    return (
        <div className={styles.page}>
            {/* ── Hero ── */}
            <section className={styles.hero}>
                <h1 className={styles.heroTitle}>
                    <span className={styles.heroTitleTop}>Complex AI Research,</span>
                    <br />
                    <span className={styles.heroTitleAccent}>Simply Explained</span>
                </h1>
                <p className={styles.heroSub}>
                    A modern research discovery experience inside Research Catalyst: fast filtering, clean
                    previews, and article-style explanations.
                </p>
                <div className={styles.heroActions}>
                    <button className="btn btn-primary" onClick={scrollToLatest} type="button">
                        Explore Papers
                    </button>
                    <button
                        className="btn btn-secondary"
                        type="button"
                        onClick={() => setUploadModalOpen(true)}
                    >
                        Upload a Paper
                    </button>
                </div>
            </section>

            {/* ── Upload Modal ── */}
            <UploadModal
                open={uploadModalOpen}
                onClose={() => setUploadModalOpen(false)}
                onSuccess={(paper) => {
                    setUploadModalOpen(false);
                    // Update the uploaded papers list
                    setUploadedPapers((prev) => [paper as SummaryPaperDetail, ...prev]);
                    router.push(`/summarizer/${paper.slug}`);
                }}
            />

            {/* ── Search ── */}
            <section className={styles.searchSection}>
                <div className={styles.searchHeader}>
                    <h2>Search Papers</h2>
                    <div className={styles.searchInputRow}>
                        <div className={styles.searchBox}>
                            <span className={styles.searchIcon}>🔍</span>
                            <input
                                className={styles.searchInput}
                                placeholder="Search papers by title, abstract, or authors..."
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                            />
                        </div>
                    </div>
                </div>
            </section>

            {/* ── Browse by Category ── */}
            <section className={styles.browseSection}>
                <div className={styles.browseHeader}>
                    <h2>Browse by Category</h2>
                    <Link className="btn btn-ghost" href="/summarizer/browse" style={{ fontSize: "0.82rem", padding: "0.35rem 0.6rem" }}>
                        View All &rarr;
                    </Link>
                </div>

                <div className={`${styles.chipsRow} ${styles.browseChipsRow}`} aria-label="Browse by category">
                    {chipCategories.map((cat) => {
                        const active = cat === selectedCategory;
                        return (
                            <button
                                key={cat}
                                type="button"
                                className={`${styles.chip} ${active ? styles.chipActive : ""}`}
                                onClick={() => onCategoryChipClick(cat)}
                            >
                                {cat}
                            </button>
                        );
                    })}
                </div>
            </section>

            {error && (
                <div className={`empty-state`} style={{ marginTop: "var(--space-xl)" }}>
                    <h3 style={{ color: "var(--text-secondary)" }}>⚠️ {error}</h3>
                </div>
            )}

            {/* ── Your Uploaded Papers ── */}
            {uploadedPapers.length > 0 && (
                <section className={styles.section}>
                    <div className={styles.sectionHead}>
                        <div>
                            <h2>Your Uploaded Papers</h2>
                            <p>AI-generated summaries from your uploaded PDFs</p>
                        </div>
                        <div style={{ color: "var(--text-muted)", fontSize: "0.82rem" }}>
                            {uploadedPapers.length} paper{uploadedPapers.length !== 1 ? "s" : ""}
                        </div>
                    </div>

                    <div className={styles.grid}>
                        {uploadedPapers.map((paper) => {
                            const accent = "#6f42c1";
                            return (
                                <Link
                                    key={paper.slug}
                                    href={`/summarizer/${paper.slug}`}
                                    className="card"
                                    style={{
                                        padding: "var(--space-lg)",
                                        borderRadius: "var(--radius-xl)",
                                        borderTop: `4px solid ${accent}`,
                                        boxShadow: "var(--shadow-xs)",
                                        textDecoration: "none",
                                        display: "block",
                                    }}
                                >
                                    <div style={{ display: "flex", justifyContent: "space-between", gap: "var(--space-sm)" }}>
                                        <span
                                            className={styles.catPill}
                                            style={{
                                                borderColor: `${accent}55`,
                                                background: `${accent}12`,
                                                color: accent,
                                            }}
                                        >
                                            📄 {paper.category || "Uploaded"}
                                        </span>
                                        <span style={{ color: "var(--text-muted)", fontSize: "0.72rem" }}>AI Generated</span>
                                    </div>

                                    <h3 className={styles.paperTitle} style={{ marginTop: "var(--space-sm)" }}>
                                        {paper.title}
                                    </h3>
                                    <div className={styles.paperAuthors}>
                                        {paper.authors?.length
                                            ? safeTrimAuthors(paper.authors)
                                            : "Uploaded paper"}
                                    </div>
                                    <div className={styles.paperPreview}>
                                        {paper.executive_summary?.slice(0, 200) || "AI-generated summary"}
                                    </div>
                                    <div className={styles.paperMeta}>
                                        <span>{paper.time_ago || "just now"}</span>
                                        <span>{paper.read_time_minutes || 1} min read</span>
                                    </div>
                                </Link>
                            );
                        })}
                    </div>
                </section>
            )}

            {/* ── Latest Research ── */}
            <section className={styles.section} id="latest-research">
                <div className={styles.sectionHead}>
                    <div>
                        <h2>Latest Research</h2>
                        <p>Fresh papers from the world&apos;s leading AI labs</p>
                    </div>
                    <div style={{ color: "var(--text-muted)", fontSize: "0.82rem" }}>
                        {latestTotal ? `${latestTotal} results` : ""}
                    </div>
                </div>

                <div className={styles.grid}>
                    {latest.map((paper) => {
                        const accent = colorForCategory(paper.category);
                        const isSaved = savedSlugs.has(paper.slug);
                        return (
                            <Link
                                key={paper.slug}
                                href={`/summarizer/${paper.slug}`}
                                className="card"
                                style={{
                                    padding: "var(--space-lg)",
                                    borderRadius: "var(--radius-xl)",
                                    borderTop: `4px solid ${accent}`,
                                    boxShadow: "var(--shadow-xs)",
                                    textDecoration: "none",
                                    display: "block",
                                }}
                            >
                                <div style={{ display: "flex", justifyContent: "space-between", gap: "var(--space-sm)" }}>
                                    <span
                                        className={styles.catPill}
                                        style={{
                                            borderColor: `${accent}55`,
                                            background: `${accent}12`,
                                            color: accent,
                                        }}
                                    >
                                        {paper.category}
                                    </span>
                                    <button
                                        type="button"
                                        className={styles.saveBtn}
                                        title={isSaved ? "Saved" : "Save Paper"}
                                        onClick={(e) => {
                                            e.preventDefault();
                                            e.stopPropagation();
                                            toggleSaved(paper.slug);
                                        }}
                                    >
                                        {isSaved ? "🔖" : "📑"}
                                    </button>
                                </div>

                                <h3 className={styles.paperTitle} style={{ marginTop: "var(--space-sm)" }}>
                                    {paper.title}
                                </h3>
                                <div className={styles.paperAuthors}>{safeTrimAuthors(paper.authors)}</div>
                                <div className={styles.paperPreview}>{paper.executive_summary_preview}</div>
                                <div className={styles.paperMeta}>
                                    <span>{paper.time_ago}</span>
                                    <span>{paper.read_time_minutes} min read</span>
                                </div>
                            </Link>
                        );
                    })}
                </div>

                {latestHasMore && (
                    <div className={styles.loadMoreWrap}>
                        <button className="btn btn-secondary" type="button" onClick={loadMoreLatest} disabled={loading}>
                            {loading ? "Loading…" : "Load More Latest Papers"}
                        </button>
                    </div>
                )}
            </section>

            {/* ── Most Popular ── */}
            <section className={styles.section}>
                <div className={styles.sectionHead}>
                    <div>
                        <h2>Most Popular</h2>
                        <p>All-time favorites from the AI research community</p>
                    </div>
                    <div style={{ color: "var(--text-muted)", fontSize: "0.82rem" }}>
                        {popularTotal ? `${popularTotal} results` : ""}
                    </div>
                </div>

                <div className={styles.grid}>
                    {popular.map((paper) => {
                        const accent = colorForCategory(paper.category);
                        const isSaved = savedSlugs.has(paper.slug);
                        return (
                            <Link
                                key={paper.slug}
                                href={`/summarizer/${paper.slug}`}
                                className="card"
                                style={{
                                    padding: "var(--space-lg)",
                                    borderRadius: "var(--radius-xl)",
                                    borderTop: `4px solid ${accent}`,
                                    boxShadow: "var(--shadow-xs)",
                                    textDecoration: "none",
                                    display: "block",
                                }}
                            >
                                <div style={{ display: "flex", justifyContent: "space-between", gap: "var(--space-sm)" }}>
                                    <span
                                        className={styles.catPill}
                                        style={{
                                            borderColor: `${accent}55`,
                                            background: `${accent}12`,
                                            color: accent,
                                        }}
                                    >
                                        {paper.category}
                                    </span>
                                    <button
                                        type="button"
                                        className={styles.saveBtn}
                                        title={isSaved ? "Saved" : "Save Paper"}
                                        onClick={(e) => {
                                            e.preventDefault();
                                            e.stopPropagation();
                                            toggleSaved(paper.slug);
                                        }}
                                    >
                                        {isSaved ? "🔖" : "📑"}
                                    </button>
                                </div>

                                <h3 className={styles.paperTitle} style={{ marginTop: "var(--space-sm)" }}>
                                    {paper.title}
                                </h3>
                                <div className={styles.paperAuthors}>{safeTrimAuthors(paper.authors)}</div>
                                <div className={styles.paperPreview}>{paper.executive_summary_preview}</div>
                                <div className={styles.paperMeta}>
                                    <span>{paper.time_ago}</span>
                                    <span>{paper.read_time_minutes} min read</span>
                                </div>
                            </Link>
                        );
                    })}
                </div>

                {popularHasMore && (
                    <div className={styles.loadMoreWrap}>
                        <button className="btn btn-secondary" type="button" onClick={loadMorePopular} disabled={loading}>
                            {loading ? "Loading…" : "Load More Popular Papers"}
                        </button>
                    </div>
                )}
            </section>
        </div>
    );
}

