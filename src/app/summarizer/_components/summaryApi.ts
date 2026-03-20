export const SUMMARY_API_BASE = "http://localhost:8000/api/summary";

export type SummaryPaperCard = {
    slug: string;
    title: string;
    authors: string[];
    category: string;
    date_published: string;
    time_ago: string;
    read_time_minutes: number;
    executive_summary_preview: string;
    arxiv_number?: string | null;
    original_paper_link?: string | null;
};

export type SummaryPapersListResponse = {
    data: SummaryPaperCard[];
    total: number;
    hasMore: boolean;
    limit: number;
    offset: number;
    mode: string;
};

export type SummaryPaperDetail = {
    slug: string;
    title: string;
    authors: string[];
    category: string;
    date_published: string;
    time_ago: string;
    read_time_minutes: number;
    executive_summary: string;
    detailed_breakdown: string;
    original_abstract: string;
    arxiv_number?: string | null;
    original_paper_link?: string | null;
};

export async function getSummaryCategories(): Promise<string[]> {
    const resp = await fetch(`${SUMMARY_API_BASE}/categories`);
    if (!resp.ok) throw new Error(`Categories request failed: ${resp.status}`);
    const data: { categories: string[] } = await resp.json();
    return data.categories ?? [];
}

export async function getSummaryPapers(params: {
    mode: "latest" | "popular";
    limit: number;
    offset: number;
    category?: string | null;
    q?: string;
}): Promise<SummaryPapersListResponse> {
    const { mode, limit, offset, category, q } = params;
    const qs = new URLSearchParams();
    qs.set("mode", mode);
    qs.set("limit", String(limit));
    qs.set("offset", String(offset));
    if (category && category !== "All Papers") qs.set("category", category);
    if (q && q.trim()) qs.set("q", q.trim());

    const path = q && q.trim() ? "/papers/search" : "/papers";
    const resp = await fetch(`${SUMMARY_API_BASE}${path}?${qs.toString()}`);
    if (!resp.ok) throw new Error(`Papers request failed: ${resp.status}`);
    const data: SummaryPapersListResponse = await resp.json();
    return data;
}

export async function getSummaryPaperBySlug(slug: string): Promise<SummaryPaperDetail> {
    const resp = await fetch(`${SUMMARY_API_BASE}/papers/${encodeURIComponent(slug)}`);
    if (!resp.ok) throw new Error(`Paper request failed: ${resp.status}`);
    return (await resp.json()) as SummaryPaperDetail;
}

