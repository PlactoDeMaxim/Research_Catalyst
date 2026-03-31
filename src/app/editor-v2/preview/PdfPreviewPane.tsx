"use client";

import { useState } from "react";
import { getDownloadPdfUrl } from "../compile/compileClient";
import styles from "../editor-v2.module.css";

type PdfPreviewPaneProps = {
    inlineUrl: string;
    jobId: string;
    status: string;
    phase: string;
    message: string;
    logs: string[];
    diagnostics?: Array<{ file?: string; line?: number; message?: string; severity?: string }>;
    onRecompile: () => void;
};

export default function PdfPreviewPane({
    inlineUrl,
    jobId,
    status,
    phase,
    message,
    logs,
    diagnostics = [],
    onRecompile,
}: PdfPreviewPaneProps) {
    const latestLog = logs[logs.length - 1] ?? "";
    const [logOpen, setLogOpen] = useState(true);
    const pdfHref = jobId && status === "succeeded" ? getDownloadPdfUrl(jobId) : "";
    const [iframeError, setIframeError] = useState<string | null>(null);

    return (
        <div className={styles.previewRoot}>
            <div className={styles.previewHeader}>
                <div className={styles.previewTitle}>PDF Preview</div>
                <div className={styles.previewActions}>
                    {pdfHref ? (
                        <a className={styles.previewBtn} href={pdfHref} download>
                            Download PDF
                        </a>
                    ) : null}
                    <button className={styles.previewBtnPrimary} onClick={onRecompile}>
                        Recompile
                    </button>
                </div>
            </div>
            <div className={styles.previewCanvas}>
                {inlineUrl && !iframeError ? (
                    <iframe
                        title="Compiled PDF"
                        src={inlineUrl}
                        className={styles.previewFrame}
                        onError={() => setIframeError("Unable to embed preview frame. Use Download PDF instead.")}
                    />
                ) : (
                    <div className={styles.previewEmpty}>
                        <div className={styles.previewEmptyTitle}>No compiled PDF yet</div>
                        <div>
                            {iframeError
                                ? iframeError
                                : status !== "idle"
                                  ? `${phase}: ${message}`
                                  : "Type in the editor and auto-compile will produce preview."}
                        </div>
                    </div>
                )}
            </div>
            <div className={`${styles.compileLogShell} ${logOpen ? styles.compileLogOpen : styles.compileLogClosed}`}>
                <button
                    type="button"
                    onClick={() => setLogOpen((o) => !o)}
                    className={styles.compileLogToggle}
                >
                    <span>
                        Compile log {phase !== "idle" ? `(${phase})` : ""}
                    </span>
                    <span aria-hidden>{logOpen ? "▼" : "▲"}</span>
                </button>
                {logOpen && (
                    <div className={styles.compileLogBody}>
                        {diagnostics.length > 0 && (
                            <div className={styles.compileDiagList}>
                                {diagnostics.slice(-8).map((item, idx) => (
                                    <div key={`${item.file}-${item.line}-${idx}`} className={styles.compileDiagItem}>
                                        {(item.file ? `${item.file}` : "tex") + (item.line ? `:${item.line}` : "")}
                                        {item.message ? ` - ${item.message}` : ""}
                                    </div>
                                ))}
                            </div>
                        )}
                        <pre className={styles.compileLogText}>{latestLog || `${phase}: ${message}`}</pre>
                    </div>
                )}
            </div>
        </div>
    );
}
