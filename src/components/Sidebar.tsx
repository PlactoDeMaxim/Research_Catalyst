"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import styles from "./Sidebar.module.css";

const navItems = [
    { href: "/", label: "Dashboard", icon: "📊" },
    { href: "/discovery", label: "Discovery", icon: "🔍" },
    { href: "/editor", label: "Paper Editor", icon: "📝" },
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

export default function Sidebar() {
    const pathname = usePathname();

    return (
        <aside className={styles.sidebar}>
            {/* Logo */}
            <div className={styles.logo}>
                <div className={styles.logoIcon}>⚛</div>
                <div className={styles.logoText}>
                    <span className={styles.logoName}>Research Catalyst</span>
                    <span className={styles.logoSub}>Research Platform</span>
                </div>
            </div>

            {/* Main Navigation */}
            <nav className={styles.nav}>
                <span className={styles.navLabel}>Main</span>
                {navItems.map((item) => (
                    <Link
                        key={item.href}
                        href={item.href}
                        className={`${styles.navItem} ${pathname === item.href ? styles.active : ""
                            }`}
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
                    <div key={item.label} className={`${styles.navItem} ${styles.disabled}`}>
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
