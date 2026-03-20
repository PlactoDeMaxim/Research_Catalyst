"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import styles from "./page.module.css";
import Link from "next/link";
import { getSummaryCategories, getSummaryPapers } from "../_components/summaryApi";

type CategoryTile = {
    name: string;
    count: number;
};

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

export default function BrowseByCategoryPage() {
    const router = useRouter();
    const [categories, setCategories] = useState<string[]>([]);
    const [tiles, setTiles] = useState<CategoryTile[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                const cats = await getSummaryCategories();
                if (cancelled) return;
                setCategories(cats);
            } catch (err) {
                if (cancelled) return;
                setError(err instanceof Error ? err.message : "Failed to load categories");
            }
        })();

        return () => {
            cancelled = true;
        };
    }, []);

    useEffect(() => {
        if (!categories.length) return;
        let cancelled = false;

        (async () => {
            setLoading(true);
            setError(null);

            try {
                // All papers count (mode latest) with limit=1 offset=0 is enough.
                const allResp = await getSummaryPapers({
                    mode: "latest",
                    limit: 1,
                    offset: 0,
                    category: null,
                });

                const newTiles: CategoryTile[] = [
                    { name: "All Papers", count: allResp.total },
                ];

                // Fetch counts per category. MVP: N+1 calls is acceptable for small category sets.
                const counts = await Promise.all(
                    categories.map(async (cat) => {
                        const r = await getSummaryPapers({
                            mode: "latest",
                            limit: 1,
                            offset: 0,
                            category: cat,
                        });
                        return { name: cat, count: r.total };
                    })
                );

                newTiles.push(...counts);

                if (cancelled) return;
                setTiles(newTiles);
            } catch (err) {
                if (cancelled) return;
                setError(err instanceof Error ? err.message : "Failed to load category counts");
            } finally {
                if (cancelled) return;
                setLoading(false);
            }
        })();

        return () => {
            cancelled = true;
        };
    }, [categories]);

    const handlePickCategory = (cat: string) => {
        if (cat === "All Papers") {
            router.push("/summarizer");
            return;
        }
        router.push(`/summarizer?category=${encodeURIComponent(cat)}`);
    };

    return (
        <div className={styles.page}>
            <div className={styles.headerRow}>
                <div>
                    <h1 className={styles.title}>Browse by Category</h1>
                    <p className={styles.subtitle}>
                        Explore research papers organized by topic.
                    </p>
                </div>
                <div className={styles.backRow}>
                    <Link className="btn btn-secondary" href="/summarizer">
                        Back
                    </Link>
                </div>
            </div>

            {error && (
                <div className={`empty-state`} style={{ marginTop: "var(--space-xl)" }}>
                    <h3 style={{ color: "var(--text-secondary)" }}>⚠️ {error}</h3>
                </div>
            )}

            {loading && (
                <div className={`empty-state`} style={{ marginTop: "var(--space-xl)" }}>
                    <div className={styles.spinner} />
                    <p>Loading categories…</p>
                </div>
            )}

            {!loading && !error && (
                <div className={styles.grid} role="list">
                    {tiles.map((t) => {
                        const accent = colorForCategory(t.name);
                        return (
                            <button
                                key={t.name}
                                type="button"
                                className={styles.tile}
                                onClick={() => handlePickCategory(t.name)}
                                style={{
                                    borderTopColor: accent,
                                }}
                            >
                                <div className={styles.tileTop}>
                                    <span
                                        className={styles.pill}
                                        style={{
                                            borderColor: `${accent}55`,
                                            background: `${accent}12`,
                                            color: accent,
                                        }}
                                    >
                                        {t.name}
                                    </span>
                                    <span className={styles.count}>{t.count} papers</span>
                                </div>
                                <div className={styles.tileBody}>
                                    <div className={styles.tileDesc}>
                                        Research papers in {t.name === "All Papers" ? "general" : t.name}.
                                    </div>
                                </div>
                            </button>
                        );
                    })}
                </div>
            )}
        </div>
    );
}

