import { NextRequest, NextResponse } from "next/server";

function getCodeMapperBase(): string {
    const base =
        process.env.CODE_MAPPER_API_BASE ||
        process.env.NEXT_PUBLIC_CODE_MAPPER_API_BASE ||
        "http://127.0.0.1:8000/api/code-mapper";
    return base.replace(/\/$/, "");
}

function formatBackendError(detail: unknown): string {
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
        return detail
            .map((item) => {
                if (item && typeof item === "object" && "msg" in item) {
                    return String((item as { msg: string }).msg);
                }
                return JSON.stringify(item);
            })
            .join("; ");
    }
    if (detail != null && typeof detail === "object") {
        return JSON.stringify(detail);
    }
    return "Backend request failed.";
}

export async function POST(request: NextRequest) {
    try {
        const body = (await request.json()) as { prompt?: string };
        const prompt = body.prompt?.trim();

        if (!prompt) {
            return NextResponse.json({ error: "Prompt is required." }, { status: 400 });
        }

        const base = getCodeMapperBase();
        const response = await fetch(`${base}/test-llm`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ prompt }),
            cache: "no-store",
        });

        const data = (await response.json()) as {
            text?: string;
            detail?: unknown;
        };
        if (!response.ok) {
            return NextResponse.json(
                {
                    error: formatBackendError(data.detail) || `Backend request failed with ${response.status}.`,
                },
                { status: response.status }
            );
        }

        return NextResponse.json({ answer: data.text || "" });
    } catch (err: unknown) {
        const message =
            err instanceof Error ? err.message : "Unable to process chat request.";
        const connection =
            message.includes("fetch failed") ||
            message.includes("ECONNREFUSED") ||
            message.includes("ENOTFOUND");
        return NextResponse.json(
            {
                error: connection
                    ? `Cannot reach ${getCodeMapperBase()}. Start FastAPI on port 8000 and set OLLAMA_API_KEY in backend/.env.`
                    : message,
            },
            { status: 500 }
        );
    }
}
