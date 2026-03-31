"use client";

import { FormEvent, useState, useRef, useEffect } from "react";
import styles from "./page.module.css";

type Role = "user" | "assistant";

interface ChatMessage {
    id: string;
    role: Role;
    content: string;
}

/* ── Multi-Research pipeline step event ── */
interface PipelineStepEvent {
    step: string;
    status: string;
    message?: string;
    report?: string;
    topic?: string;
}

export default function HomePage() {
    const [query, setQuery] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [messages, setMessages] = useState<ChatMessage[]>([]);

    /* ── Multi-Research Agent state ── */
    const [multiResearchActive, setMultiResearchActive] = useState(false);
    const [pipelineRunning, setPipelineRunning] = useState(false);
    const [pipelineSteps, setPipelineSteps] = useState<PipelineStepEvent[]>([]);
    const [pipelineReport, setPipelineReport] = useState<string | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, pipelineSteps, pipelineReport]);

    /* ── Regular Ollama Chat ── */
    async function handleRegularChat(prompt: string) {
        const userMessage: ChatMessage = {
            id: `${Date.now()}-user`,
            role: "user",
            content: prompt,
        };
        setMessages((prev) => [...prev, userMessage]);

        try {
            const response = await fetch("/api/ollama-chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ prompt }),
            });

            const data = (await response.json()) as { answer?: string; error?: string };
            if (!response.ok) {
                throw new Error(data.error || `Request failed: ${response.status}`);
            }

            const assistantMessage: ChatMessage = {
                id: `${Date.now()}-assistant`,
                role: "assistant",
                content: data.answer || "No response generated.",
            };
            setMessages((prev) => [...prev, assistantMessage]);
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : "Chat request failed.";
            setError(message);
        }
    }

    /* ── Multi-Research Agent Pipeline ── */
    async function handleMultiResearch(topic: string) {
        setPipelineRunning(true);
        setPipelineSteps([]);
        setPipelineReport(null);

        const userMessage: ChatMessage = {
            id: `${Date.now()}-user`,
            role: "user",
            content: `🔬 Multi-Research: ${topic}`,
        };
        setMessages((prev) => [...prev, userMessage]);

        try {
            const response = await fetch("http://localhost:8000/api/multi-research/run", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ topic }),
            });

            if (!response.ok) {
                throw new Error(`Multi-research pipeline failed: ${response.status}`);
            }

            const reader = response.body?.getReader();
            const decoder = new TextDecoder();

            if (!reader) throw new Error("No response stream");

            let buffer = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n");
                buffer = lines.pop() || "";

                for (const line of lines) {
                    if (line.startsWith("data: ")) {
                        try {
                            const eventData: PipelineStepEvent = JSON.parse(line.slice(6));
                            if (eventData.step === "complete" && eventData.report) {
                                setPipelineReport(eventData.report);
                                const assistantMessage: ChatMessage = {
                                    id: `${Date.now()}-assistant`,
                                    role: "assistant",
                                    content: eventData.report,
                                };
                                setMessages((prev) => [...prev, assistantMessage]);
                            } else if (eventData.step === "error") {
                                setError(eventData.message || "Pipeline failed");
                            } else {
                                setPipelineSteps((prev) => {
                                    const next = prev.map((item) => ({ ...item, status: "completed" }));
                                    return [...next, eventData];
                                });
                            }
                        } catch {
                            // ignore malformed SSE lines
                        }
                    }
                }
            }
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : "Multi-research pipeline failed.";
            setError(message);
        } finally {
            setPipelineRunning(false);
        }
    }

    /* ── Form submit handler ── */
    async function handleSubmit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        const prompt = query.trim();
        if (!prompt || loading || pipelineRunning) return;

        setError(null);
        setLoading(true);
        setQuery("");

        try {
            if (multiResearchActive) {
                await handleMultiResearch(prompt);
            } else {
                await handleRegularChat(prompt);
            }
        } finally {
            setLoading(false);
        }
    }

    const isProcessing = loading || pipelineRunning;

    return (
        <div className={styles.home}>
            <h1 className={styles.title}>Research starts here</h1>

            <div className={styles.chatShell}>
                {(messages.length > 0 || pipelineSteps.length > 0) && (
                    <div className={styles.messages}>
                        {messages.map((message) => (
                            <div
                                key={message.id}
                                className={`${styles.message} ${
                                    message.role === "user" ? styles.user : styles.assistant
                                }`}
                            >
                                <span className={styles.messageRole}>
                                    {message.role === "user" ? "You" : "Assistant"}
                                </span>
                                {message.role === "assistant" ? (
                                    <div
                                        className={styles.markdownContent}
                                        dangerouslySetInnerHTML={{ __html: simpleMarkdownToHtml(message.content) }}
                                    />
                                ) : (
                                    <p>{message.content}</p>
                                )}
                            </div>
                        ))}

                        {/* Pipeline progress indicators */}
                        {pipelineRunning && pipelineSteps.length > 0 && (
                            <div className={`${styles.message} ${styles.assistant}`}>
                                <span className={styles.messageRole}>Pipeline Progress</span>
                                <div className={styles.pipelineProgress}>
                                    {pipelineSteps.map((step, i) => (
                                        <div key={i} className={styles.pipelineStep}>
                                            <span className={styles.stepIndicator}>
                                                {step.status === "running" ? "⏳" : "✅"}
                                            </span>
                                            <span>{step.message || step.step}</span>
                                        </div>
                                    ))}
                                    <div className={styles.pipelineStep}>
                                        <span className={styles.stepSpinner} />
                                        <span>Working...</span>
                                    </div>
                                </div>
                            </div>
                        )}

                        <div ref={messagesEndRef} />
                    </div>
                )}

                <form className={styles.inputBar} onSubmit={handleSubmit}>
                    <input
                        type="text"
                        value={query}
                        onChange={(event) => setQuery(event.target.value)}
                        placeholder={
                            multiResearchActive
                                ? "Enter research topic for multi-agent analysis..."
                                : "Ask the research..."
                        }
                        className={styles.input}
                        disabled={isProcessing}
                    />
                    <button
                        type="submit"
                        className={styles.sendButton}
                        disabled={isProcessing || !query.trim()}
                        aria-label="Send message"
                    >
                        {isProcessing ? "..." : "→"}
                    </button>
                </form>

                <div className={styles.quickControls}>
                    <button
                        type="button"
                        className={`${styles.controlChip} ${
                            multiResearchActive ? styles.controlChipActive : ""
                        }`}
                        onClick={() => setMultiResearchActive(!multiResearchActive)}
                    >
                        👓 Multi Research Agent
                    </button>
                    <button type="button" className={styles.controlChip}>
                        Corpus ▾
                    </button>
                    <button type="button" className={styles.controlChip} aria-label="Add source">
                        +
                    </button>
                </div>

                {multiResearchActive && (
                    <div className={styles.multiResearchBanner}>
                        🤖 Multi-Agent Research mode is active — your query will be processed by 5 AI agents
                        (Planner → Search → Validator → Extractor → Synthesizer)
                    </div>
                )}
            </div>

            {error && <p className={styles.error}>{error}</p>}
        </div>
    );
}

/* Simple Markdown → HTML for rendering research reports */
function simpleMarkdownToHtml(md: string): string {
    let html = md
        // Headers
        .replace(/^### (.+)$/gm, "<h3>$1</h3>")
        .replace(/^## (.+)$/gm, "<h2>$1</h2>")
        .replace(/^# (.+)$/gm, "<h1>$1</h1>")
        // Bold
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        // Italic
        .replace(/\*(.+?)\*/g, "<em>$1</em>")
        // Inline code
        .replace(/`([^`]+)`/g, "<code>$1</code>")
        // Links
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
        // Horizontal rules
        .replace(/^---$/gm, "<hr />")
        // Line breaks
        .replace(/\n/g, "<br />");

    // Simple table support
    if (html.includes("|")) {
        html = html.replace(
            /(\|.+\|<br \/>)+/g,
            (match) => {
                const rows = match.split("<br />").filter((r) => r.trim());
                if (rows.length < 2) return match;

                let table = '<table class="md-table"><thead><tr>';
                const headerCells = rows[0].split("|").filter((c) => c.trim());
                for (const cell of headerCells) {
                    table += `<th>${cell.trim()}</th>`;
                }
                table += "</tr></thead><tbody>";

                for (let i = 1; i < rows.length; i++) {
                    const cells = rows[i].split("|").filter((c) => c.trim());
                    if (cells.every((c) => /^[-:]+$/.test(c.trim()))) continue;
                    table += "<tr>";
                    for (const cell of cells) {
                        table += `<td>${cell.trim()}</td>`;
                    }
                    table += "</tr>";
                }
                table += "</tbody></table>";
                return table;
            }
        );
    }

    return html;
}
