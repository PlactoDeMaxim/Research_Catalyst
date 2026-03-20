"use client";

import { useMemo } from "react";

function escapeHtml(s: string) {
    return s
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function renderInline(escapedText: string) {
    // escapedText is already HTML-escaped.
    // Minimal inline markdown:
    // - bold: **text**
    // - inline code: `code`
    return escapedText
        .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
        .replace(/`([^`]+)`/g, "<code>$1</code>");
}

function markdownToSafeHtml(md: string) {
    const src = md || "";
    const lines = src.replace(/\r\n/g, "\n").split("\n");

    const out: string[] = [];
    let paragraphLines: string[] = [];
    let listItems: string[] = [];
    let orderedItems: string[] = [];

    const flushParagraph = () => {
        if (paragraphLines.length === 0) return;
        const joined = paragraphLines.join(" ").replace(/\s+/g, " ").trim();
        if (joined) {
            out.push(`<p>${renderInline(escapeHtml(joined))}</p>`);
        }
        paragraphLines = [];
    };

    const flushList = () => {
        if (listItems.length === 0) return;
        out.push(`<ul>${listItems.map((li) => `<li>${li}</li>`).join("")}</ul>`);
        listItems = [];
    };

    const flushOrderedList = () => {
        if (orderedItems.length === 0) return;
        out.push(`<ol>${orderedItems.map((li) => `<li>${li}</li>`).join("")}</ol>`);
        orderedItems = [];
    };

    const isBlank = (s: string) => s.trim().length === 0;

    for (const rawLine of lines) {
        const line = rawLine; // keep raw whitespace for list matching
        const trimmed = line.trim();
        //remove hash in preprocessing and remove lines from 58 to 64 after
        // Some scraped markdown blocks end with a stray "#" line.
        // Skip standalone hash-only lines to avoid rendering a visible "#".
        if (/^#{1,3}$/.test(trimmed)) {
            continue;
        }

        if (isBlank(line)) {
            flushParagraph();
            flushList();
            flushOrderedList();
            continue;
        }

        // Headings: ### Title / ## Title / # Title
        const headingMatch = line.match(/^(#{1,3})\s+(.*)$/);
        if (headingMatch) {
            flushParagraph();
            flushList();
            flushOrderedList();
            const headingText = headingMatch[2].trim();
            if (headingText) {
                out.push(`<h3>${renderInline(escapeHtml(headingText))}</h3>`);
            }
            continue;
        }

        // Unordered lists: - item, * item, + item
        const listMatch = line.match(/^\s*[-*+]\s+(.*)$/);
        if (listMatch) {
            // Starting/continuing list cancels paragraph mode.
            flushParagraph();
            flushOrderedList();

            const itemText = listMatch[1].trim();
            if (itemText) listItems.push(renderInline(escapeHtml(itemText)));
            continue;
        }

        // Ordered lists: 1. item, 2. item, ...
        // Handles both "one item per line" and multiple numbered items on the same line.
        const orderedInlineCount = (line.match(/\d+\.\s+/g) || []).length;
        if (orderedInlineCount >= 1) {
            const orderedMatches = Array.from(line.matchAll(/(\d+)\.\s+/g));
            const isOrderedAtLineStart = /^\s*\d+\.\s+/.test(line);

            // If it contains numbers but is not clearly an ordered list, treat as paragraph.
            if (!isOrderedAtLineStart) {
                paragraphLines.push(line.trim());
                continue;
            }

            flushParagraph();
            flushList();

            if (orderedMatches.length >= 2) {
                // Split inline: "1. ... 2. ... 3. ..."
                for (let i = 0; i < orderedMatches.length; i++) {
                    const m = orderedMatches[i];
                    const start = (m.index ?? 0) + m[0].length;
                    const end =
                        i + 1 < orderedMatches.length
                            ? orderedMatches[i + 1].index ?? line.length
                            : line.length;
                    const itemText = line.slice(start, end).trim();
                    if (itemText) orderedItems.push(renderInline(escapeHtml(itemText)));
                }
            } else {
                // One item on this line
                const orderedMatch = line.match(/^\s*(\d+)\.\s+(.*)$/);
                const itemText = orderedMatch?.[2]?.trim();
                if (itemText) orderedItems.push(renderInline(escapeHtml(itemText)));
            }

            continue;
        }

        // Default: part of a paragraph
        paragraphLines.push(line.trim());
    }

    flushParagraph();
    flushList();
    flushOrderedList();

    return out.join("");
}

export default function MarkdownLite({ markdown }: { markdown: string }) {
    const html = useMemo(() => markdownToSafeHtml(markdown), [markdown]);
    return <div dangerouslySetInnerHTML={{ __html: html }} />;
}

