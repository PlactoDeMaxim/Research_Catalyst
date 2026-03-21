/**
 * Base URL for Paper Editor FastAPI routes (must match backend `prefix="/api/paper-editor"`).
 * Set `NEXT_PUBLIC_PAPER_EDITOR_API_BASE` when the Next app and API are not on localhost.
 */
export function getPaperEditorApiBase(): string {
    if (typeof process !== "undefined" && process.env.NEXT_PUBLIC_PAPER_EDITOR_API_BASE) {
        return process.env.NEXT_PUBLIC_PAPER_EDITOR_API_BASE.replace(/\/$/, "");
    }
    return "http://localhost:8000/api/paper-editor";
}

/** Evaluated once per bundle for modules that need a stable string at import time. */
export const PAPER_EDITOR_API_BASE = getPaperEditorApiBase();
