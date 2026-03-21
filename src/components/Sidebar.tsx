"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useLayoutEffect, useState } from "react";
import styles from "./Sidebar.module.css";

const STORAGE_KEY = "rc-sidebar-collapsed";

const navItems = [
    { href: "/", label: "Dashboard", icon: "📊" },
    { href: "/discovery", label: "Discovery", icon: "🔍" },
    { href: "/editor-v2", label: "Paper Editor", icon: "📝" },
    { href: "/visualize", label: "Visualize", icon: "📈" },
    { href: "/planner", label: "Planner", icon: "📅" },
    { href: "/summarizer", label: "Summary", icon: "🧠" },
];

const moduleItems = [
    { label: "Summarizer", icon: "📋", disabled: true },
    { label: "Code Mapper", icon: "🔗", disabled: true },
    { label: "Plagiarism", icon: "🛡️", disabled: true },
    { label: "Citations", icon: "📚", disabled: true },
];

function applySidebarWidth(collapsed: boolean) {
    const w = collapsed ? "var(--sidebar-width-collapsed)" : "240px";
    document.documentElement.style.setProperty("--sidebar-width", w);
}

export default function Sidebar() {
    const pathname = usePathname();
    const [collapsed, setCollapsed] = useState(false);

    useLayoutEffect(() => {
        try {
            const stored = localStorage.getItem(STORAGE_KEY) === "1";
            setCollapsed(stored);
            applySidebarWidth(stored);
        } catch {
            applySidebarWidth(false);
        }
    }, []);

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
                {navItems.map((item) => (
                    <Link
                        key={item.href}
                        href={item.href}
                        className={`${styles.navItem} ${pathname === item.href ? styles.active : ""
                            }`}
                        title={collapsed ? item.label : undefined}
                    >
                        <span className={styles.navIcon}>{item.icon}</span>
                        <span className={styles.navText}>{item.label}</span>
                        {pathname === item.href && (
                            <span className={styles.activeIndicator} />
                        )}
                    </Link>
                ))}
            </nav>

            {/* Modules (Coming Soon) */}
            <div className={styles.nav}>
                <span className={styles.navLabel}>Modules</span>
                {moduleItems.map((item) => (
                    <div
                        key={item.label}
                        className={`${styles.navItem} ${styles.disabled}`}
                        title={collapsed ? `${item.label} (coming soon)` : undefined}
                    >
                        <span className={styles.navIcon}>{item.icon}</span>
                        <span className={styles.navText}>{item.label}</span>
                        <span className={styles.badge}>Soon</span>
                    </div>
                ))}
            </div>

            {/* Footer */}
            <div className={styles.footer}>
                <div className={styles.footerInfo}>
                    <span className={styles.version}>v0.1.0 — Phase 1</span>
                </div>
            </div>
        </aside>
    );
}
