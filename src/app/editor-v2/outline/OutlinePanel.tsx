"use client";

import { useMemo, useState, type ReactNode } from "react";
import styles from "../editor-v2.module.css";

type OutlineFlatItem = {
    id: string;
    title: string;
    level: number;
    line: number;
};

type OutlineNode = OutlineFlatItem & {
    children: OutlineNode[];
};

type OutlinePanelProps = {
    latexSource: string;
    onJumpToLine: (line: number) => void;
};

export default function OutlinePanel({ latexSource, onJumpToLine }: OutlinePanelProps) {
    const items = useMemo<OutlineFlatItem[]>(() => {
        const lines = latexSource.split(/\r?\n/);
        const out: OutlineFlatItem[] = [];
        lines.forEach((line, idx) => {
            const m = line.match(/\\(section|subsection|subsubsection)\*?\{([^}]+)\}/);
            if (!m) return;
            const level = m[1] === "section" ? 1 : m[1] === "subsection" ? 2 : 3;
            out.push({
                id: `${idx}-${m[2]}`,
                title: m[2],
                level,
                line: idx + 1,
            });
        });
        return out;
    }, [latexSource]);

    const tree = useMemo<OutlineNode[]>(() => {
        const roots: OutlineNode[] = [];
        const stack: OutlineNode[] = [];
        for (const item of items) {
            const node: OutlineNode = { ...item, children: [] };
            while (stack.length > 0 && stack[stack.length - 1].level >= node.level) {
                stack.pop();
            }
            if (stack.length === 0) {
                roots.push(node);
            } else {
                stack[stack.length - 1].children.push(node);
            }
            stack.push(node);
        }
        return roots;
    }, [items]);

    const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

    const toggleCollapsed = (id: string) => {
        setCollapsed((prev) => ({ ...prev, [id]: !prev[id] }));
    };

    const renderNodes = (nodes: OutlineNode[], depth: number): ReactNode =>
        nodes.map((node) => {
            const hasChildren = node.children.length > 0;
            const isCollapsed = Boolean(collapsed[node.id]);
            return (
                <div key={node.id}>
                    <button
                        className={styles.outlineItem}
                        style={{ paddingLeft: `${8 + depth * 18}px` }}
                        onClick={() => onJumpToLine(node.line)}
                    >
                        {hasChildren ? (
                            <span
                                className={styles.outlineChevron}
                                onClick={(e) => {
                                    e.preventDefault();
                                    e.stopPropagation();
                                    toggleCollapsed(node.id);
                                }}
                            >
                                {isCollapsed ? "▸" : "▾"}
                            </span>
                        ) : (
                            <span className={styles.outlineChevronGhost}>•</span>
                        )}
                        <span className={styles.outlineItemLabel}>{node.title}</span>
                    </button>
                    {hasChildren && !isCollapsed ? renderNodes(node.children, depth + 1) : null}
                </div>
            );
        });

    return (
        <div className={styles.outlinePanel}>
            <div className={styles.outlineHeader}>
                <span className={styles.outlineHeaderChevron}>▾</span>
                <span className={styles.outlineTitle}>File outline</span>
            </div>
            {items.length === 0 ? (
                <div className={styles.outlineEmpty}>No sections found.</div>
            ) : (
                <div className={styles.outlineTree}>{renderNodes(tree, 0)}</div>
            )}
        </div>
    );
}

