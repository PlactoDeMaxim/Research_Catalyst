"""
Paper Service (Summary Discovery)

Loads `parsed_papers.json` once and keeps it cached in memory.
Implements:
  - slug generation
  - category filtering
  - case-insensitive partial search across title/authors/executive_summary
  - latest sorting (date_published)
  - popular sorting (curated top list; MVP fallback uses deterministic top-12 order)
  - pagination
"""

from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Any


DATA_LOCK = threading.Lock()
_RECORDS: list["_PaperRecord"] = []
_SLUG_TO_RECORD: dict[str, "_PaperRecord"] = {}
_CATEGORIES: list[str] = []
_POPULAR_SLUGS: list[str] = []
_INITIALIZED = False


def _workspace_root() -> Path:
    # research-catalyst/backend/modules/summary/services/paper_service.py
    # -> services (0) -> summary (1) -> modules (2) -> backend (3) -> research-catalyst (4) -> workspace root (5)
    p = Path(__file__).resolve()
    for _ in range(10):
        if (p / "parsed_papers.json").exists():
            return p
        p = p.parent
    # Fallback: use cwd
    return Path.cwd()


def _parsed_papers_path() -> Path:
    root = _workspace_root()
    return root / "parsed_papers.json"


def slugify_title(title: str) -> str:
    t = (title or "").strip().lower()
    # Replace any run of non-alphanumerics with a hyphen
    t = re.sub(r"[^a-z0-9]+", "-", t)
    t = re.sub(r"-{2,}", "-", t).strip("-")
    return t or "untitled-paper"


def _normalize_backslash_suffix(s: str) -> str:
    # Many scraped strings end with '\\' (escaped backslash in JSON).
    return re.sub(r"\\+\s*$", "", s or "").strip()


def _parse_date_published(raw: str) -> Optional[datetime]:
    s = _normalize_backslash_suffix(raw or "")
    if not s:
        return None

    # Expected example: "February 14, 2025"
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s, fmt)
            # Assume dataset is in local/neutral time; treat as UTC for relative math.
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    # Last resort: pull a year
    m = re.search(r"(19|20)\d{2}", s)
    if m:
        try:
            year = int(m.group(0))
            return datetime(year, 1, 1, tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def _time_ago(dt: Optional[datetime], now: Optional[datetime] = None) -> str:
    if dt is None:
        return "unknown"
    if now is None:
        now = datetime.now(timezone.utc)

    delta = now - dt
    seconds = int(delta.total_seconds())
    if seconds < 0:
        seconds = 0

    minutes = seconds // 60
    hours = minutes // 60
    days = hours // 24

    if days >= 365:
        years = days // 365
        return f"{years} year{'s' if years != 1 else ''} ago"
    if days >= 30:
        months = days // 30
        return f"{months} month{'s' if months != 1 else ''} ago"
    if days >= 1:
        return f"{days} day{'s' if days != 1 else ''} ago"
    if hours >= 1:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    if minutes >= 1:
        return f"{minutes} min ago"
    return "just now"


def _strip_markdown(md: str) -> str:
    if not md:
        return ""
    s = md
    # Links: [text](url) -> text
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", s)
    # Inline code
    s = re.sub(r"`([^`]+)`", r"\1", s)
    # Bold/italic markers
    s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)
    s = re.sub(r"\*([^*]+)\*", r"\1", s)
    # Headings markers
    s = re.sub(r"^\s*#{1,6}\s*", "", s, flags=re.MULTILINE)
    # Lists markers
    s = re.sub(r"^\s*[-*]\s+", "", s, flags=re.MULTILINE)
    # Collapse whitespace
    s = re.sub(r"[ \t]+", " ", s)
    s = s.strip()
    return s


def _preview_text(md: str, max_lines: int = 2) -> str:
    plain = _strip_markdown(md)
    if not plain:
        return ""
    lines = [ln.strip() for ln in plain.splitlines() if ln.strip()]
    if not lines:
        return plain[:240]
    return "\n".join(lines[:max_lines])


def _read_time_minutes_from_text(text: str) -> int:
    words = re.findall(r"\b[\w']+\b", text or "")
    count = len(words)
    if count <= 0:
        return 1
    # ~200 wpm
    return max(1, int(round(count / 200)))


@dataclass(frozen=True)
class _PaperRecord:
    slug: str
    title: str
    authors: list[str]
    category: str
    date_published_raw: str
    date_published_dt: Optional[datetime]
    arxiv_number: Optional[str]
    original_paper_link: Optional[str]
    executive_summary: str
    detailed_breakdown: str
    original_abstract: str

    # Search-friendly blob (lowercased)
    search_blob_lc: str

    # Precomputed derived fields
    preview_plain: str
    preview_for_read_time: str
    read_time_minutes: int


def _clean_author(a: str) -> str:
    return _normalize_backslash_suffix(a or "").strip()


def _build_records() -> None:
    global _RECORDS, _SLUG_TO_RECORD, _CATEGORIES, _POPULAR_SLUGS, _INITIALIZED

    path = _parsed_papers_path()
    if not path.exists():
        raise FileNotFoundError(f"parsed_papers.json not found at: {path}")

    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("parsed_papers.json must be a list")

    records: list[_PaperRecord] = []

    for item in raw:
        title = (item.get("title") or "").strip()
        if not title:
            continue

        slug = slugify_title(title)

        authors_raw = item.get("authors") or []
        authors = [_clean_author(a) for a in authors_raw if _clean_author(a)]

        category = (item.get("category") or "").strip()
        if not category:
            category = "Uncategorized"

        date_raw = _normalize_backslash_suffix(item.get("date_published") or "")
        date_dt = _parse_date_published(date_raw)

        arxiv_number = _normalize_backslash_suffix(item.get("arxiv_number") or "")
        if not arxiv_number:
            arxiv_number = None

        original_paper_link = (item.get("original_paper_link") or "").strip() or None

        executive_summary = item.get("executive_summary") or ""
        detailed_breakdown = item.get("detailed_breakdown") or ""
        original_abstract = item.get("original_abstract") or ""

        preview = _preview_text(executive_summary, max_lines=2)
        preview_for_rt = preview or _strip_markdown(executive_summary)[:900]
        rt_minutes = _read_time_minutes_from_text(preview_for_rt)

        search_blob = " ".join(
            [
                title,
                category,
                " ".join(authors),
                executive_summary,
            ]
        )
        search_blob_lc = _strip_markdown(search_blob).lower()

        records.append(
            _PaperRecord(
                slug=slug,
                title=title,
                authors=authors,
                category=category,
                date_published_raw=date_raw,
                date_published_dt=date_dt,
                arxiv_number=arxiv_number,
                original_paper_link=original_paper_link,
                executive_summary=executive_summary,
                detailed_breakdown=detailed_breakdown,
                original_abstract=original_abstract,
                search_blob_lc=search_blob_lc,
                preview_plain=preview,
                preview_for_read_time=preview_for_rt,
                read_time_minutes=rt_minutes,
            )
        )

    # Categories
    # Categories used for browsing/filtering should exclude internal/low-signal tags
    # present in the scraped dataset.
    excluded_categories = {
        "Uncategorized",
        "guideai-researchgetting-started",
        "weekly-digestai-researchtrending",
    }

    categories = sorted({r.category for r in records if r.category})
    categories = [c for c in categories if c not in excluded_categories]

    # Curated "popular" top-12
    # MVP fallback: deterministic top-12 by file order.
    popular_slugs = [r.slug for r in records[:12]]

    slug_map = {r.slug: r for r in records}

    _RECORDS = records
    _SLUG_TO_RECORD = slug_map
    _CATEGORIES = categories
    _POPULAR_SLUGS = popular_slugs
    _INITIALIZED = True


def ensure_loaded() -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return
    with DATA_LOCK:
        if _INITIALIZED:
            return
        _build_records()


def _is_category_valid(category: str) -> bool:
    if not category:
        return False
    lc = category.strip().lower()
    return any(c.lower() == lc for c in _CATEGORIES)


def _normalize_category(category: str) -> Optional[str]:
    if not category:
        return None
    lc = category.strip().lower()
    for c in _CATEGORIES:
        if c.lower() == lc:
            return c
    return None


def _filter_records(
    *,
    query: Optional[str],
    category: Optional[str],
) -> list[_PaperRecord]:
    ensure_loaded()
    q = (query or "").strip()
    q_lc = q.lower() if q else ""

    category_norm = _normalize_category(category) if category else None

    tokens = [t for t in re.split(r"\s+", q_lc) if t] if q_lc else []

    results: list[_PaperRecord] = []
    for r in _RECORDS:
        if category_norm and r.category.lower() != category_norm.lower():
            continue
        if tokens:
            blob = r.search_blob_lc
            if not all(tok in blob for tok in tokens):
                continue
        results.append(r)
    return results


def _sort_records(mode: str, records: list[_PaperRecord]) -> list[_PaperRecord]:
    ensure_loaded()
    if mode == "popular":
        index = {slug: i for i, slug in enumerate(_POPULAR_SLUGS)}

        def key(rec: _PaperRecord) -> int:
            return index.get(rec.slug, len(_POPULAR_SLUGS) + 1)

        return sorted(records, key=key)

    # latest (default)
    def key_latest(rec: _PaperRecord) -> float:
        return rec.date_published_dt.timestamp() if rec.date_published_dt else -1

    return sorted(records, key=key_latest, reverse=True)


def list_papers(
    *,
    mode: str = "latest",
    limit: int = 20,
    offset: int = 0,
    category: Optional[str] = None,
) -> dict[str, Any]:
    results = _filter_records(query=None, category=category)
    ordered = _sort_records(mode, results)
    return _paginate_to_response(mode=mode, ordered=ordered, limit=limit, offset=offset)


def search_papers(
    *,
    query: str,
    mode: str = "latest",
    limit: int = 20,
    offset: int = 0,
    category: Optional[str] = None,
) -> dict[str, Any]:
    results = _filter_records(query=query, category=category)
    ordered = _sort_records(mode, results)
    return _paginate_to_response(mode=mode, ordered=ordered, limit=limit, offset=offset)


def _paginate_to_response(*, mode: str, ordered: list[_PaperRecord], limit: int, offset: int) -> dict[str, Any]:
    ensure_loaded()
    total = len(ordered)
    limit = max(1, int(limit))
    offset = max(0, int(offset))

    slice_ = ordered[offset : offset + limit]
    has_more = offset + limit < total

    now = datetime.now(timezone.utc)
    data = []
    for r in slice_:
        data.append(
            {
                "slug": r.slug,
                "title": r.title,
                "authors": r.authors,
                "category": r.category,
                "date_published": r.date_published_raw,
                "time_ago": _time_ago(r.date_published_dt, now=now),
                "read_time_minutes": r.read_time_minutes,
                "executive_summary_preview": r.preview_plain,
                "arxiv_number": r.arxiv_number,
                "original_paper_link": r.original_paper_link,
            }
        )

    return {
        "data": data,
        "total": total,
        "hasMore": has_more,
        "limit": limit,
        "offset": offset,
        "mode": mode,
    }


def get_categories() -> dict[str, Any]:
    ensure_loaded()
    return {"categories": _CATEGORIES}


def get_paper_detail(slug: str) -> Optional[dict[str, Any]]:
    ensure_loaded()
    if not slug:
        return None

    # Slug might be URL-encoded; normalizing to lowercase for map lookup.
    slug_norm = slug.strip().lower()
    rec = _SLUG_TO_RECORD.get(slug_norm)
    if not rec:
        return None

    now = datetime.now(timezone.utc)
    return {
        "slug": rec.slug,
        "title": rec.title,
        "authors": rec.authors,
        "category": rec.category,
        "date_published": rec.date_published_raw,
        "time_ago": _time_ago(rec.date_published_dt, now=now),
        "read_time_minutes": rec.read_time_minutes,
        "executive_summary": rec.executive_summary,
        "detailed_breakdown": rec.detailed_breakdown,
        "original_abstract": rec.original_abstract,
        "arxiv_number": rec.arxiv_number,
        "original_paper_link": rec.original_paper_link,
    }

