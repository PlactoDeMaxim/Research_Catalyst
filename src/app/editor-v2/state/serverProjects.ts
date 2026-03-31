import type { ProjectState } from "./projectStore";

export type ServerEditorProject = {
    id: string;
    title: string;
    description: string;
    storage_key?: string;
    editor_state?: ProjectState | null;
    created_at?: string;
    updated_at?: string;
};

const CORE_API_BASE =
    process.env.NEXT_PUBLIC_CORE_API_BASE?.replace(/\/$/, "") ?? "/api/core-proxy";

async function parseJson<T>(response: Response): Promise<T> {
    if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`);
    }
    return (await response.json()) as T;
}

async function safeRequest<T>(input: RequestInfo | URL, init?: RequestInit): Promise<T | null> {
    try {
        const response = await fetch(input, init);
        return await parseJson<T>(response);
    } catch {
        return null;
    }
}

export async function listServerEditorProjects(): Promise<ServerEditorProject[]> {
    const json = await safeRequest<{ items?: ServerEditorProject[] }>(`${CORE_API_BASE}/editor-projects`, {
        cache: "no-store",
    });
    return json.items ?? [];
}

export async function getServerEditorProject(projectId: string): Promise<ServerEditorProject | null> {
    const json = await safeRequest<{ item?: ServerEditorProject | null }>(
        `${CORE_API_BASE}/editor-projects/${projectId}`,
        { cache: "no-store" }
    );
    return json.item ?? null;
}

export async function createServerEditorProject(payload: {
    title: string;
    description?: string;
    storage_key?: string;
    state: ProjectState;
}): Promise<ServerEditorProject> {
    const response = await fetch(`${CORE_API_BASE}/editor-projects`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    return parseJson<ServerEditorProject>(response);
}

export async function updateServerEditorProject(
    projectId: string,
    payload: {
        title?: string;
        description?: string;
        storage_key?: string;
        state?: ProjectState;
    }
): Promise<ServerEditorProject | null> {
    const json = await safeRequest<{ item?: ServerEditorProject | null }>(`${CORE_API_BASE}/editor-projects/${projectId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    return json?.item ?? null;
}

export async function deleteServerEditorProject(projectId: string): Promise<boolean> {
    const json = await safeRequest<{ deleted?: boolean }>(`${CORE_API_BASE}/editor-projects/${projectId}`, {
        method: "DELETE",
    });
    return Boolean(json?.deleted);
}
