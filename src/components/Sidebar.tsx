"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useLayoutEffect, useState } from "react";
import styles from "./Sidebar.module.css";

const STORAGE_KEY = "rc-sidebar-collapsed";

const navItems = [
    { href: "/", label: "Home", icon: "🏠" },
    { href: "/discovery", label: "Discovery", icon: "🔍" },
    { href: "/editor-v2", label: "Paper Editor", icon: "📝" },
    { href: "/visualize", label: "Visualize", icon: "📈" },
    { href: "/planner", label: "Planner", icon: "📅" },
    { href: "/summarizer", label: "Summarizer", icon: "🧠" },
    { href: "/code-mapper", label: "Code Mapper", icon: "🔗" },
    { href: "/citation-manager", label: "Citations", icon: "📚" },
    { href: "/plagiarism-check", label: "Plagiarism", icon: "🛡️" },
];


function applySidebarWidth(collapsed: boolean) {
    const w = collapsed ? "var(--sidebar-width-collapsed)" : "240px";
    document.documentElement.style.setProperty("--sidebar-width", w);
}

export default function Sidebar() {
    const pathname = usePathname();
    const [collapsed, setCollapsed] = useState(() => {
        if (typeof window === "undefined") return false;
        try {
            return localStorage.getItem(STORAGE_KEY) === "1";
        } catch {
            return false;
        }
    });

    useLayoutEffect(() => {
        applySidebarWidth(collapsed);
    }, [collapsed]);

    const toggle = useCallback(() => {
        setCollapsed((prev) => {
            const next = !prev;
            applySidebarWidth(next);
            try {
                localStorage.setItem(STORAGE_KEY, next ? "1" : "0");
            } catch {
                /* ignore */
            }
            return next;
        });
    }, []);

    return (
        <aside
            className={`${styles.sidebar} ${collapsed ? styles.collapsed : ""}`}
            aria-label="Main navigation"
        >
            <div className={styles.headerRow}>
                <div className={styles.logo}>
                    <div className={styles.logoIcon} aria-hidden>
                        ⚛
                    </div>
                    <div className={styles.logoText}>
                        <span className={styles.logoName}>Research Catalyst</span>
                        <span className={styles.logoSub}>Research Platform</span>
                    </div>
                </div>
                <button
                    type="button"
                    className={styles.collapseToggle}
                    onClick={toggle}
                    aria-expanded={!collapsed}
                    aria-controls="sidebar-main-nav"
                    title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
                >
                    <span className={styles.collapseIcon} aria-hidden>
                        ◀
                    </span>
                    <span className="sr-only">
                        {collapsed ? "Expand sidebar" : "Collapse sidebar"}
                    </span>
                </button>
            </div>

            {/* Main Navigation */}
            <nav id="sidebar-main-nav" className={styles.nav}>
                <span className={styles.navLabel}>Main</span>
                {navItems.map((item) => {
                    const isActive =
                        item.href === "/"
                            ? pathname === "/"
                            : pathname === item.href || pathname.startsWith(item.href + "/");
                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={`${styles.navItem} ${isActive ? styles.active : ""}`}
                            title={collapsed ? item.label : undefined}
                        >
                            <span className={styles.navIcon}>{item.icon}</span>
                            <span className={styles.navText}>{item.label}</span>
                            {isActive && (
                                <span className={styles.activeIndicator} />
                            )}
                        </Link>
                    );
                })}
            </nav>


            {/* Footer */}
            <div className={styles.footer}>
                <div className={styles.footerInfo}>
                    <span className={styles.version}>v0.1.0 — Phase 1</span>
                </div>
            </div>
        </aside>
    );
}
