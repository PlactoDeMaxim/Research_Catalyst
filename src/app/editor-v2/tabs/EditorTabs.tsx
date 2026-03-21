"use client";

import type { ProjectFile } from "../state/projectStore";
import styles from "../editor-v2.module.css";

type EditorTabsProps = {
    files: ProjectFile[];
    openTabIds: string[];
    activeTabId: string | null;
    onActivateTab: (id: string) => void;
    onCloseTab: (id: string) => void;
};

export default function EditorTabs({
    files,
    openTabIds,
    activeTabId,
    onActivateTab,
    onCloseTab,
}: EditorTabsProps) {
    const tabs = openTabIds
        .map((id) => files.find((f) => f.id === id))
        .filter((f): f is ProjectFile => Boolean(f));

    return (
        <div className={styles.editorTabsBar}>
            {tabs.map((tab) => {
                const isActive = tab.id === activeTabId;
                return (
                    <div
                        key={tab.id}
                        onClick={() => onActivateTab(tab.id)}
                        className={`${styles.editorTab} ${isActive ? styles.editorTabActive : ""}`}
                    >
                        <span className={styles.editorTabName}>{tab.name}</span>
                        <button
                            className={styles.fileTreeIconBtn}
                            onClick={(e) => {
                                e.stopPropagation();
                                onCloseTab(tab.id);
                            }}
                        >
                            ×
                        </button>
                    </div>
                );
            })}
        </div>
    );
}

