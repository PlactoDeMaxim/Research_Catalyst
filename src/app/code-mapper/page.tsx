"use client";

import Link from "next/link";
import styles from "./page.module.css";

export default function CodeMapperLanding() {
    return (
        <div>
            <div className={`${styles.header} animate-in`}>
                <h1>Code Mapper</h1>
                <p className={styles.subtitle}>
                    Bidirectional bridge between research papers and code.
                    Convert papers into runnable implementations, or generate
                    academic papers from GitHub repositories.
                </p>
            </div>

            <div className={styles.featureGrid}>
                <Link
                    href="/code-mapper/paper-to-code"
                    className={`${styles.featureCard} animate-in`}
                >
                    <span className={styles.featureArrow}>&rarr;</span>
                    <span className={styles.featureIcon}>📄</span>
                    <h2 className={styles.featureTitle}>Paper &rarr; Code</h2>
                    <p className={styles.featureDesc}>
                        Upload a research paper (PDF or Word) and generate a
                        complete, runnable ML/DL implementation. Extracts
                        methodology, architecture, and training procedures
                        to produce production-grade code.
                    </p>
                    <div className={styles.featureTags}>
                        <span className={styles.tag}>PDF / Word</span>
                        <span className={styles.tag}>PyTorch</span>
                        <span className={styles.tag}>Auto-validation</span>
                        <span className={styles.tag}>ZIP download</span>
                    </div>
                </Link>

                <Link
                    href="/code-mapper/repo-to-paper"
                    className={`${styles.featureCard} animate-in`}
                >
                    <span className={styles.featureArrow}>&rarr;</span>
                    <span className={styles.featureIcon}>🔗</span>
                    <h2 className={styles.featureTitle}>Repo &rarr; Paper</h2>
                    <p className={styles.featureDesc}>
                        Provide a GitHub repository URL and generate an
                        academic-quality research paper with real, verified
                        citations. Outputs in LaTeX and Word formats with
                        proper bibliography.
                    </p>
                    <div className={styles.featureTags}>
                        <span className={styles.tag}>GitHub</span>
                        <span className={styles.tag}>LaTeX / Word</span>
                        <span className={styles.tag}>Verified citations</span>
                        <span className={styles.tag}>Multi-source</span>
                    </div>
                </Link>
            </div>

            <div className={`${styles.infoSection} animate-in`}>
                <h3 className={styles.infoTitle}>Powered by</h3>
                <div className={styles.infoGrid}>
                    <div className={styles.infoItem}>
                        <span className={styles.infoIcon}>🧠</span>
                        <span>
                            <strong>LLM-driven extraction</strong> &mdash;
                            Multi-phase pipelines with structured output and
                            iterative refinement
                        </span>
                    </div>
                    <div className={styles.infoItem}>
                        <span className={styles.infoIcon}>🔍</span>
                        <span>
                            <strong>4-layer citation verification</strong> &mdash;
                            arXiv ID, DOI, Semantic Scholar, and LLM relevance
                            scoring
                        </span>
                    </div>
                    <div className={styles.infoItem}>
                        <span className={styles.infoIcon}>✅</span>
                        <span>
                            <strong>AST validation + exec-fix loop</strong> &mdash;
                            Generated code is syntax-checked and test-executed with
                            auto-repair
                        </span>
                    </div>
                </div>
            </div>
        </div>
    );
}
