"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ProjectFile } from "../state/projectStore";
import { compileFromSource, getInlinePdfUrl, pollCompileStatus } from "./compileClient";

type SchedulerOptions = {
    projectName: string;
    files: ProjectFile[];
    mainPath: string;
    autoCompile: boolean;
    compileDelayMs: number;
};

export function useCompileScheduler({
    projectName,
    files,
    mainPath,
    autoCompile,
    compileDelayMs,
}: SchedulerOptions) {
    const [jobId, setJobId] = useState<string>("");
    const [status, setStatus] = useState<"idle" | "queued" | "running" | "succeeded" | "failed">("idle");
    const [message, setMessage] = useState<string>("Idle");
    const [logs, setLogs] = useState<string[]>([]);
    const [diagnostics, setDiagnostics] = useState<
        Array<{ file?: string; line?: number; message?: string; severity?: string }>
    >([]);
    const [inlineUrl, setInlineUrl] = useState<string>("");
    const hashRef = useRef<string>("");
    const requestInFlightRef = useRef<boolean>(false);
    const pendingCompileRef = useRef<boolean>(false);
    const mainPathRef = useRef<string>(mainPath);
    const prevMainPathRef = useRef<string | null>(null);

    useEffect(() => {
        mainPathRef.current = mainPath;
    }, [mainPath]);

    const executeCompile = useCallback(async () => {
        const activeJob = status === "queued" || status === "running";
        if (requestInFlightRef.current || activeJob) {
            pendingCompileRef.current = true;
            return;
        }

        requestInFlightRef.current = true;
        try {
            setDiagnostics([]);
            setStatus("queued");
            setMessage("Queueing compile job...");
            const created = await compileFromSource(projectName, files, mainPath);
            setJobId(created.job_id);
            setStatus(created.status);
            setMessage(created.message);
        } catch (err) {
            setStatus("failed");
            setMessage(err instanceof Error ? err.message : "Compile request failed");
        } finally {
            requestInFlightRef.current = false;
        }
    }, [projectName, files, mainPath, status]);

    /** Root document changed: cancel in-flight job tracking and queue a fresh compile. */
    useEffect(() => {
        if (prevMainPathRef.current === null) {
            prevMainPathRef.current = mainPath;
            return;
        }
        if (prevMainPathRef.current === mainPath) return;
        prevMainPathRef.current = mainPath;
        setJobId("");
        setStatus("idle");
        setMessage("Main file changed — preparing compile…");
        setLogs([]);
        setDiagnostics([]);
        setInlineUrl("");
        hashRef.current = "";
        pendingCompileRef.current = true;
        requestInFlightRef.current = false;
        const t = window.setTimeout(() => void executeCompile(), 0);
        return () => window.clearTimeout(t);
    }, [mainPath, executeCompile]);

    useEffect(() => {
        if (!jobId) return;
        if (status === "succeeded" || status === "failed") return;
        let cancelled = false;
        let timer: ReturnType<typeof setTimeout> | null = null;
        const poll = async () => {
            if (cancelled) return;
            try {
                const next = await pollCompileStatus(jobId);
                if (cancelled) return;
                setStatus(next.status);
                setMessage(next.message);
                setLogs(next.logs ?? []);
                setDiagnostics(next.diagnostics ?? []);
                if (next.status === "succeeded") {
                    setInlineUrl(`${getInlinePdfUrl(jobId)}?t=${Date.now()}`);
                    if (pendingCompileRef.current) {
                        pendingCompileRef.current = false;
                        timer = setTimeout(() => {
                            void executeCompile();
                        }, 0);
                    }
                    return;
                }
                if (next.status === "failed") {
                    if (pendingCompileRef.current) {
                        pendingCompileRef.current = false;
                        timer = setTimeout(() => {
                            void executeCompile();
                        }, 0);
                    }
                    return;
                }
            } catch (err) {
                setStatus("failed");
                setMessage(err instanceof Error ? err.message : "Compile status polling failed");
                return;
            }
            timer = setTimeout(poll, 2500);
        };
        void poll();
        return () => {
            cancelled = true;
            if (timer) clearTimeout(timer);
        };
    }, [jobId, status, executeCompile]);

    useEffect(() => {
        if (!autoCompile) return;
        const nextHash = JSON.stringify({
            mainPath: mainPathRef.current,
            files: files.map((f) => `${f.path}:${f.updatedAt}`),
        });
        if (nextHash === hashRef.current) return;
        const timer = setTimeout(() => {
            hashRef.current = nextHash;
            void executeCompile();
        }, Math.max(500, compileDelayMs));
        return () => clearTimeout(timer);
    }, [autoCompile, compileDelayMs, executeCompile, files]);

    const phase = useMemo<"idle" | "queued" | "compiling" | "succeeded" | "failed">(() => {
        if (status === "idle") return "idle";
        if (status === "queued") return "queued";
        if (status === "running") return "compiling";
        if (status === "succeeded") return "succeeded";
        return "failed";
    }, [status]);

    return {
        status,
        phase,
        message,
        logs,
        diagnostics,
        jobId,
        inlineUrl,
        runManualCompile: executeCompile,
    };
}

