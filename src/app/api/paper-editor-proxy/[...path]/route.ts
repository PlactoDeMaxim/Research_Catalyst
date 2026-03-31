import { NextRequest, NextResponse } from "next/server";

function getPaperEditorBackendBase(): string {
    return (
        process.env.PAPER_EDITOR_API_BASE ||
        process.env.NEXT_PUBLIC_PAPER_EDITOR_API_BASE ||
        "http://127.0.0.1:8000/api/paper-editor"
    ).replace(/\/$/, "");
}

async function proxy(request: NextRequest, pathParts: string[]) {
    const base = getPaperEditorBackendBase();
    const query = request.nextUrl.search || "";
    const target = `${base}/${pathParts.join("/")}${query}`;
    const init: RequestInit = {
        method: request.method,
        headers: request.headers,
        body:
            request.method === "GET" || request.method === "HEAD"
                ? undefined
                : await request.text(),
        duplex: "half" as RequestDuplex,
        cache: "no-store",
    };

    const response = await fetch(target, init);
    const body = await response.arrayBuffer();
    const headers = new Headers(response.headers);
    headers.delete("content-encoding");
    headers.delete("content-length");
    return new NextResponse(body, {
        status: response.status,
        headers,
    });
}

export async function GET(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
    const { path } = await context.params;
    return proxy(request, path);
}

export async function POST(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
    const { path } = await context.params;
    return proxy(request, path);
}

export async function PUT(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
    const { path } = await context.params;
    return proxy(request, path);
}

export async function DELETE(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
    const { path } = await context.params;
    return proxy(request, path);
}
