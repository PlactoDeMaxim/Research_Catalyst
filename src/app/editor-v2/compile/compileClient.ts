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
        throw new Error(`Compile source failed (${resp.status})`);
    }
    return (await resp.json()) as CompileSourceResponse;
}

export async function pollCompileStatus(jobId: string) {
    const resp = await fetch(`${PAPER_EDITOR_API_BASE}/status/${encodeURIComponent(jobId)}`);
    if (!resp.ok) throw new Error(`Status failed (${resp.status})`);
    return (await resp.json()) as CompileStatus;
}

export function getInlinePdfUrl(jobId: string) {
    return `${PAPER_EDITOR_API_BASE}/download/${encodeURIComponent(jobId)}`;
}

export function getDownloadPdfUrl(jobId: string) {
    return `${PAPER_EDITOR_API_BASE}/download/${encodeURIComponent(jobId)}?download=1`;
}

