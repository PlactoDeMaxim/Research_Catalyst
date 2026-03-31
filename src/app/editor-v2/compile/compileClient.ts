import { PAPER_EDITOR_API_BASE } from "@/lib/paperEditorApi";
import type { ProjectFile } from "../state/projectStore";

export type CompileSourceRequest = {
    project_name: string;
    main_file_path: string;
    files: Array<{ path: string; content: string; binary_base64?: string | null }>;
    max_retries?: number;
};

export type CompileSourceResponse = {
    template_id: string;
    job_id: string;
    status: "queued" | "running" | "succeeded" | "failed";
    message: string;
};

export type CompileStatus = {
    job_id: string;
    status: "queued" | "running" | "succeeded" | "failed";
    message: string;
    logs: string[];
    artifact_path?: string | null;
    diagnostics?: Array<{
        file?: string;
        line?: number;
        message?: string;
        severity?: string;
    }>;
};

function readJobId(data: Record<string, unknown>): string {
    const raw = data.job_id ?? data.jobId;
    return typeof raw === "string" ? raw : raw != null ? String(raw) : "";
}

function coerceStatus(v: unknown): CompileSourceResponse["status"] {
    const s = typeof v === "string" ? v : String(v ?? "");
    if (s === "queued" || s === "running" || s === "succeeded" || s === "failed") return s;
    return "queued";
}

export async function compileFromSource(projectName: string, files: ProjectFile[], mainPath: string) {
    const payload: CompileSourceRequest = {
        project_name: projectName,
        main_file_path: mainPath,
        files: files.map((f) => ({
            path: f.path,
            content: f.content,
            binary_base64: f.binaryBase64 ?? null,
        })),
        max_retries: 1,
    };
    const resp = await fetch(`${PAPER_EDITOR_API_BASE}/v2/compile-source`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    if (!resp.ok) {
        const detail = await resp.text().catch(() => "");
        throw new Error(`Compile source failed (${resp.status})${detail ? `: ${detail.slice(0, 400)}` : ""}`);
    }
    let data: Record<string, unknown>;
    try {
        data = (await resp.json()) as Record<string, unknown>;
    } catch {
        throw new Error("Compile response was not valid JSON. Is the paper-editor API URL correct?");
    }
    const job_id = readJobId(data);
    if (!job_id.trim()) {
        throw new Error(
            "Backend returned no job_id. Check that the FastAPI server is running (port 8000) and NEXT_PUBLIC_PAPER_EDITOR_API_BASE if set."
        );
    }
    const template_id =
        typeof data.template_id === "string"
            ? data.template_id
            : typeof data.templateId === "string"
              ? data.templateId
              : "";
    const message = typeof data.message === "string" ? data.message : "";
    const status = coerceStatus(data.status);
    return { template_id, job_id, status, message };
}

export async function pollCompileStatus(jobId: string) {
    const resp = await fetch(`${PAPER_EDITOR_API_BASE}/status/${encodeURIComponent(jobId)}`);
    if (!resp.ok) throw new Error(`Status failed (${resp.status})`);
    let data: Record<string, unknown>;
    try {
        data = (await resp.json()) as Record<string, unknown>;
    } catch {
        throw new Error("Status response was not valid JSON.");
    }
    const id = readJobId(data);
    const status = coerceStatus(data.status);
    const message = typeof data.message === "string" ? data.message : "";
    const logs = Array.isArray(data.logs) ? (data.logs as string[]) : [];
    const diagnostics = Array.isArray(data.diagnostics) ? data.diagnostics : [];
    return {
        job_id: id || jobId,
        status,
        message,
        logs,
        artifact_path: data.artifact_path ?? null,
        diagnostics: diagnostics as CompileStatus["diagnostics"],
    } satisfies CompileStatus;
}

export function getInlinePdfUrl(jobId: string) {
    return `${PAPER_EDITOR_API_BASE}/download/${encodeURIComponent(jobId)}`;
}

export function getDownloadPdfUrl(jobId: string) {
    return `${PAPER_EDITOR_API_BASE}/download/${encodeURIComponent(jobId)}?download=1`;
}
