"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import styles from "./page.module.css";
import MarkdownLite from "../_components/MarkdownLite";
import {
    getSummaryPaperBySlug,
    getSummaryPapers,
    type SummaryPaperCard,
    type SummaryPaperDetail,
} from "../_components/summaryApi";

function getSavedSlugs(): Set<string> {
    try {
        const raw = localStorage.getItem("savedSummaryPapers");
        if (!raw) return new Set();
        return new Set(JSON.parse(raw) as string[]);
    } catch {
        return new Set();
    }
}

export default function SummaryPaperPage() {
    const params = useParams();
    const slug = (params as { slug?: string } | null)?.slug;

    const [paper, setPaper] = useState<SummaryPaperDetail | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const [relevantPapers, setRelevantPapers] = useState<SummaryPaperCard[]>([]);
    const [relevantLoading, setRelevantLoading] = useState(false);
    const [relevantError, setRelevantError] = useState<string | null>(null);

    const [savedSlugs, setSavedSlugs] = useState<Set<string>>(new Set());
    useEffect(() => setSavedSlugs(getSavedSlugs()), []);

    useEffect(() => {
        if (!slug) return;
        let cancelled = false;
        (async () => {
            setLoading(true);
            setError(null);
            try {
                const data = await getSummaryPaperBySlug(slug);
                if (cancelled) return;
                setPaper(data);
            } catch (err) {
                if (cancelled) return;
                setError(err instanceof Error ? err.message : "Failed to load paper");
            } finally {
                if (!cancelled) setLoading(false);
            }
        })();
        return () => {
            cancelled = true;
        };
    }, [slug]);

    const isSaved = useMemo(() => (paper ? savedSlugs.has(paper.slug) : false), [paper, savedSlugs]);

    // Derive "Relevant Papers" using a backend search tuned to this paper.
    useEffect(() => {
        if (!paper) return;
        let cancelled = false;
        (async () => {
            setRelevantLoading(true);
            setRelevantError(null);
            try {
                // Title match + same category usually yields good "related" results.
                const resp = await getSummaryPapers({
                    mode: "latest",
                    limit: 8,
                    offset: 0,
                    category: paper.category,
                    q: paper.title,
                });
                const cleaned = resp.data.filter((p) => p.slug !== paper.slug).slice(0, 4);
                if (cancelled) return;
                setRelevantPapers(cleaned);
            } catch (err) {
                if (cancelled) return;
                setRelevantError(err instanceof Error ? err.message : "Failed to load relevant papers");
            } finally {
                if (cancelled) return;
                setRelevantLoading(false);
            }
        })();

        return () => {
            cancelled = true;
        };
    }, [paper]);

    const toggleSaved = () => {
        if (!paper) return;
        setSavedSlugs((prev) => {
            const next = new Set(prev);
            if (next.has(paper.slug)) next.delete(paper.slug);
            else next.add(paper.slug);
            try {
                localStorage.setItem("savedSummaryPapers", JSON.stringify(Array.from(next)));
            } catch {
                // ignore
            }
            return next;
        });
    };

    const copyLink = async () => {
        try {
            await navigator.clipboard.writeText(window.location.href);
        } catch {
            // ignore
        }
    };

    const pdfUrl = paper?.arxiv_number ? `https://arxiv.org/pdf/${encodeURIComponent(paper.arxiv_number)}.pdf` : null;

    if (loading) {
        return (
            <div className={styles.wrapper}>
                <div className="empty-state">
                    <div className={styles.spinner} />
                    <p>Loading paper…</p>
                </div>
            </div>
        );
    }

    if (error || !paper) {
        return (
            <div className={styles.wrapper}>
                <div className="empty-state">
                    <h3 style={{ color: "var(--text-secondary)" }}>⚠️ {error || "Paper not found"}</h3>
                </div>
            </div>
        );
    }

    return (
        <div className={styles.wrapper}>
            <div className={styles.topRow}>
                <div className={styles.titleBlock}>
                    <h1>{paper.title}</h1>
                    <div className={styles.metaLine}>
                        {paper.authors.length
                            ? `By ${paper.authors.slice(0, 3).join(", ")}${
                                  paper.authors.length > 3 ? ` +${paper.authors.length - 3} more` : ""
                              }`
                            : ""}
                        {" · "}
                        {paper.time_ago}
                        {" · "}
                        {paper.read_time_minutes} min read
                    </div>
                </div>

                <div className={styles.actionsRow}>
                    <button className="btn btn-primary" type="button" onClick={toggleSaved}>
                        {isSaved ? "Saved" : "Save Paper"}
                    </button>
                    <a
                        className={`btn btn-secondary ${pdfUrl ? "" : ""}`}
                        href={pdfUrl || undefined}
                        onClick={(e) => {
                            if (!pdfUrl) e.preventDefault();
                        }}
                        style={{ pointerEvents: pdfUrl ? "auto" : "none", opacity: pdfUrl ? 1 : 0.55 }}
                    >
                        Download PDF
                    </a>
                    <button className="btn btn-ghost" type="button" onClick={copyLink}>
                        Copy Link
                    </button>
                    <Link
                        className="btn btn-secondary"
                        href={paper.original_paper_link || `https://arxiv.org/abs/${encodeURIComponent(paper.arxiv_number || "")}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ textDecoration: "none" }}
                    >
                        Original Paper
                    </Link>
                </div>
            </div>

            <div className={styles.sectionStack}>
                <div className={styles.sectionBox}>
                    <h2>Original Abstract</h2>
                    <div className={styles.markdown}>
                        <MarkdownLite markdown={paper.original_abstract || "No original abstract available."} />
                    </div>
                </div>

                <div className={styles.sectionBox}>
                    <h2>Executive Summary</h2>
                    <div className={styles.markdown}>
                        <MarkdownLite markdown={paper.executive_summary} />
                    </div>
                </div>

                <div className={styles.sectionBox}>
                    <h2>Detailed Breakdown</h2>
                    <div className={styles.markdown}>
                        <MarkdownLite markdown={paper.detailed_breakdown || "No detailed breakdown available."} />
                    </div>
                </div>
            </div>

            <section className={styles.relevantSection} aria-label="Relevant Papers">
                <div className={styles.relevantHeader}>
                    <h2>Relevant Papers</h2>
                    {relevantLoading && <div className={styles.smallSpinner} aria-hidden />}
                </div>
                {relevantError && (
                    <div className="empty-state" style={{ padding: "var(--space-lg) 0", marginTop: 0 }}>
                        <h3 style={{ color: "var(--text-secondary)", fontSize: "0.95rem" }}>⚠️ {relevantError}</h3>
                    </div>
                )}
                {!relevantError && !relevantLoading && relevantPapers.length > 0 && (
                    <div className={styles.relevantGrid}>
                        {relevantPapers.map((p) => {
                            return (
                                <Link
                                    key={p.slug}
                                    href={`/summarizer/${p.slug}`}
                                    className={styles.relevantCard}
                                    style={{
                                        textDecoration: "none",
                                        borderTop: "4px solid rgba(44, 106, 115, 0.6)",
                                    }}
                                >
                                    <div style={{ display: "flex", justifyContent: "space-between", gap: "var(--space-sm)" }}>
                                        <span className="badge" style={{ background: "var(--bg-muted)" }}>
                                            {p.category}
                                        </span>
                                        <span style={{ color: "var(--text-muted)", fontSize: "0.78rem" }}>{p.time_ago}</span>
                                    </div>
                                    <div style={{ fontWeight: 900, marginTop: "var(--space-sm)", lineHeight: 1.25 }}>
                                        {p.title}
                                    </div>
                                    <div style={{ color: "var(--text-muted)", fontSize: "0.86rem", marginTop: "var(--space-sm)", lineHeight: 1.35 }}>
                                        {p.executive_summary_preview}
                                    </div>
                                </Link>
                            );
                        })}
                    </div>
                )}
            </section>

            <div className={styles.footerRow}>
                <div>
                    Category: <strong>{paper.category}</strong>
                </div>
                <div>
                    {paper.arxiv_number ? (
                        <>
                            ArXiv:{" "}
                            <a href={`https://arxiv.org/abs/${encodeURIComponent(paper.arxiv_number)}`} target="_blank" rel="noopener noreferrer">
                                {paper.arxiv_number}
                            </a>
                        </>
                    ) : (
                        <span>ArXiv: n/a</span>
                    )}
                </div>
            </div>
        </div>
    );
}

