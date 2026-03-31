"use client";

import { useCallback, useRef, useState } from "react";
import { uploadPaperPdf, type SummaryPaperDetail } from "./summaryApi";

type Props = {
    open: boolean;
    onClose: () => void;
    onSuccess: (paper: SummaryPaperDetail) => void;
};

export default function UploadModal({ open, onClose, onSuccess }: Props) {
    const [dragOver, setDragOver] = useState(false);
    const [file, setFile] = useState<File | null>(null);
    const [uploading, setUploading] = useState(false);
    const [progress, setProgress] = useState("");
    const [error, setError] = useState<string | null>(null);
    const inputRef = useRef<HTMLInputElement>(null);

    const reset = useCallback(() => {
        setFile(null);
        setUploading(false);
        setProgress("");
        setError(null);
        setDragOver(false);
    }, []);

    const handleClose = useCallback(() => {
        if (uploading) return; // Don't close while processing
        reset();
        onClose();
    }, [uploading, reset, onClose]);

    const handleFile = useCallback((f: File) => {
        if (!f.name.toLowerCase().endsWith(".pdf")) {
            setError("Only PDF files are accepted.");
            return;
        }
        if (f.size > 50 * 1024 * 1024) {
            setError("File is too large (max 50 MB).");
            return;
        }
        setError(null);
        setFile(f);
    }, []);

    const handleDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setDragOver(true);
    }, []);

    const handleDragLeave = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setDragOver(false);
    }, []);

    const handleDrop = useCallback(
        (e: React.DragEvent) => {
            e.preventDefault();
            e.stopPropagation();
            setDragOver(false);
            const f = e.dataTransfer.files?.[0];
            if (f) handleFile(f);
        },
        [handleFile]
    );

    const handleInputChange = useCallback(
        (e: React.ChangeEvent<HTMLInputElement>) => {
            const f = e.target.files?.[0];
            if (f) handleFile(f);
        },
        [handleFile]
    );

    const handleUpload = useCallback(async () => {
        if (!file || uploading) return;
        setUploading(true);
        setError(null);
        setProgress("Uploading PDF...");

        try {
            setProgress("Extracting text & generating AI summary — this may take 30-60 seconds...");
            const paper = await uploadPaperPdf(file);
            setProgress("Summary generated successfully!");
            // Small delay so user sees the success message
            await new Promise((r) => setTimeout(r, 600));
            reset();
            onSuccess(paper);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Upload failed");
            setUploading(false);
            setProgress("");
        }
    }, [file, uploading, reset, onSuccess]);

    if (!open) return null;

    return (
        <div className="upload-modal-overlay" onClick={handleClose}>
            <div
                className="upload-modal"
                onClick={(e) => e.stopPropagation()}
                role="dialog"
                aria-modal="true"
                aria-label="Upload a Paper"
            >
                {/* Header */}
                <div className="upload-modal-header">
                    <h2>Upload a Research Paper</h2>
                    <button
                        className="upload-modal-close"
                        onClick={handleClose}
                        disabled={uploading}
                        aria-label="Close"
                    >
                        ✕
                    </button>
                </div>

                {/* Content */}
                <div className="upload-modal-body">
                    {!uploading && !file && (
                        <div
                            className={`upload-dropzone ${dragOver ? "upload-dropzone-active" : ""}`}
                            onDragOver={handleDragOver}
                            onDragLeave={handleDragLeave}
                            onDrop={handleDrop}
                            onClick={() => inputRef.current?.click()}
                        >
                            <div className="upload-dropzone-icon">📄</div>
                            <div className="upload-dropzone-title">
                                Drop your PDF here, or <span className="upload-dropzone-link">browse</span>
                            </div>
                            <div className="upload-dropzone-hint">PDF files up to 50 MB</div>
                            <input
                                ref={inputRef}
                                type="file"
                                accept=".pdf,application/pdf"
                                onChange={handleInputChange}
                                style={{ display: "none" }}
                            />
                        </div>
                    )}

                    {!uploading && file && (
                        <div className="upload-file-preview">
                            <div className="upload-file-icon">📝</div>
                            <div className="upload-file-info">
                                <div className="upload-file-name">{file.name}</div>
                                <div className="upload-file-size">
                                    {(file.size / 1024 / 1024).toFixed(2)} MB
                                </div>
                            </div>
                            <button
                                className="upload-file-remove"
                                onClick={() => {
                                    setFile(null);
                                    setError(null);
                                }}
                                aria-label="Remove file"
                            >
                                ✕
                            </button>
                        </div>
                    )}

                    {uploading && (
                        <div className="upload-progress">
                            <div className="upload-spinner" />
                            <div className="upload-progress-text">{progress}</div>
                        </div>
                    )}

                    {error && <div className="upload-error">⚠️ {error}</div>}
                </div>

                {/* Footer */}
                <div className="upload-modal-footer">
                    <button
                        className="btn btn-ghost"
                        onClick={handleClose}
                        disabled={uploading}
                    >
                        Cancel
                    </button>
                    <button
                        className="btn btn-primary"
                        onClick={handleUpload}
                        disabled={!file || uploading}
                    >
                        {uploading ? "Processing..." : "Generate Summary"}
                    </button>
                </div>
            </div>
        </div>
    );
}
