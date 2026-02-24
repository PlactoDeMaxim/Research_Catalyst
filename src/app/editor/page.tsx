"use client";

import { useState, useCallback, useMemo } from "react";
import dynamic from "next/dynamic";
import styles from "./page.module.css";

const LatexPreview = dynamic(() => import("@/components/LatexPreview"), {
    ssr: false,
    loading: () => (
        <div className={styles.previewLoading}>Loading preview…</div>
    ),
});

/* ═══════════════════════════════════════
   Templates
   ═══════════════════════════════════════ */
interface Template {
    id: string;
    name: string;
    description: string;
    icon: string;
    sections: SectionDef[];
    preamble: string;
}

interface SectionDef {
    id: string;
    label: string;
    placeholder: string;
    isAbstract?: boolean;
}

const TEMPLATES: Template[] = [
    {
        id: "ieee",
        name: "IEEE Conference",
        description: "Standard IEEE two-column conference paper format",
        icon: "📐",
        preamble: "\\documentclass[conference]{IEEEtran}\n\\usepackage{amsmath,graphicx,cite}",
        sections: [
            { id: "abstract", label: "Abstract", placeholder: "Provide a concise summary of your research (150–250 words)…", isAbstract: true },
            { id: "intro", label: "Introduction", placeholder: "Introduce the research problem, motivation, and your contributions…" },
            { id: "related", label: "Related Work", placeholder: "Discuss prior work and how your approach differs…" },
            { id: "method", label: "Methodology", placeholder: "Describe your approach, algorithms, or experimental design…" },
            { id: "results", label: "Results", placeholder: "Present your findings, data, and analysis…" },
            { id: "discussion", label: "Discussion", placeholder: "Interpret results, limitations, and implications…" },
            { id: "conclusion", label: "Conclusion", placeholder: "Summarize contributions and suggest future work…" },
        ],
    },
    {
        id: "acm",
        name: "ACM SIGCHI",
        description: "ACM CHI / HCI conference format",
        icon: "🖥️",
        preamble: "\\documentclass[sigchi]{acmart}\n\\usepackage{amsmath,graphicx}",
        sections: [
            { id: "abstract", label: "Abstract", placeholder: "Summarize your research contribution…", isAbstract: true },
            { id: "intro", label: "Introduction", placeholder: "Introduce the problem space and research questions…" },
            { id: "background", label: "Background", placeholder: "Provide context, theory, and related work…" },
            { id: "design", label: "System Design", placeholder: "Describe the design of your system or study…" },
            { id: "study", label: "User Study", placeholder: "Detail your study methodology, participants, and procedure…" },
            { id: "results", label: "Findings", placeholder: "Present qualitative and quantitative results…" },
            { id: "discussion", label: "Discussion", placeholder: "Discuss implications for design, limitations…" },
            { id: "conclusion", label: "Conclusion", placeholder: "Summarize and outline future directions…" },
        ],
    },
    {
        id: "thesis",
        name: "Thesis / Report",
        description: "Standard academic thesis or research report",
        icon: "📖",
        preamble: "\\documentclass[12pt]{report}\n\\usepackage{amsmath,graphicx,hyperref}",
        sections: [
            { id: "abstract", label: "Abstract", placeholder: "Summarize your thesis in 300 words or less…", isAbstract: true },
            { id: "intro", label: "Introduction", placeholder: "Define the problem, objectives, and scope of your research…" },
            { id: "lit-review", label: "Literature Review", placeholder: "Review existing literature and theoretical framework…" },
            { id: "method", label: "Research Methodology", placeholder: "Describe your research design, data collection, and analysis methods…" },
            { id: "results", label: "Results & Analysis", placeholder: "Present your findings and data analysis…" },
            { id: "discussion", label: "Discussion", placeholder: "Interpret results in context of your research questions…" },
            { id: "conclusion", label: "Conclusion & Recommendations", placeholder: "Summarize findings and recommend future work…" },
        ],
    },
    {
        id: "arxiv",
        name: "arXiv Preprint",
        description: "Clean single-column preprint format",
        icon: "📄",
        preamble: "\\documentclass[11pt]{article}\n\\usepackage{amsmath,amssymb,graphicx,hyperref}",
        sections: [
            { id: "abstract", label: "Abstract", placeholder: "Summarize the key contributions and results…", isAbstract: true },
            { id: "intro", label: "Introduction", placeholder: "Introduce the problem and state your contributions…" },
            { id: "prelim", label: "Preliminaries", placeholder: "Define notation, background concepts, and problem formulation…" },
            { id: "method", label: "Proposed Method", placeholder: "Describe your approach in detail…" },
            { id: "experiments", label: "Experiments", placeholder: "Describe datasets, baselines, metrics, and experimental setup…" },
            { id: "results", label: "Results", placeholder: "Present quantitative and qualitative results…" },
            { id: "conclusion", label: "Conclusion", placeholder: "Summarize and discuss future work…" },
        ],
    },
    {
        id: "blank",
        name: "Blank Paper",
        description: "Start from scratch with a minimal structure",
        icon: "✏️",
        preamble: "\\documentclass[12pt]{article}\n\\usepackage{amsmath,graphicx}",
        sections: [
            { id: "abstract", label: "Abstract", placeholder: "Write your abstract…", isAbstract: true },
            { id: "intro", label: "Introduction", placeholder: "Start writing…" },
        ],
    },
];

/* ═══════════════════════════════════════
   Section content state
   ═══════════════════════════════════════ */
type SectionContents = Record<string, string>;

/* ═══════════════════════════════════════
   Build LaTeX source from sections
   ═══════════════════════════════════════ */
function buildLatex(
    template: Template,
    title: string,
    authors: string,
    sections: SectionContents
): string {
    let latex = template.preamble + "\n\n";
    latex += `\\title{${title || "Untitled Paper"}}\n`;
    latex += `\\author{${authors || "Author Name"}}\n`;
    latex += "\\date{\\today}\n\n";
    latex += "\\begin{document}\n\n\\maketitle\n\n";

    for (const sec of template.sections) {
        const content = sections[sec.id] || "";
        if (sec.isAbstract) {
            latex += "\\begin{abstract}\n";
            latex += content || sec.placeholder;
            latex += "\n\\end{abstract}\n\n";
        } else {
            latex += `\\section{${sec.label}}\n\n`;
            latex += (content || "") + "\n\n";
        }
    }

    latex += "\\end{document}\n";
    return latex;
}

/* ═══════════════════════════════════════
   Component
   ═══════════════════════════════════════ */
export default function EditorPage() {
    const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);
    const [showLatex, setShowLatex] = useState(false);
    const [title, setTitle] = useState("");
    const [authors, setAuthors] = useState("");
    const [sectionContents, setSectionContents] = useState<SectionContents>({});
    const [manualLatex, setManualLatex] = useState("");
    const [aiLoading, setAiLoading] = useState<string | null>(null);
    const [activeSection, setActiveSection] = useState<string | null>(null);
    const [customSections, setCustomSections] = useState<SectionDef[]>([]);

    const allSections = useMemo(() => {
        if (!selectedTemplate) return [];
        return [...selectedTemplate.sections, ...customSections];
    }, [selectedTemplate, customSections]);

    const latexSource = useMemo(() => {
        if (showLatex && manualLatex) return manualLatex;
        if (!selectedTemplate) return "";
        return buildLatex(
            { ...selectedTemplate, sections: allSections },
            title,
            authors,
            sectionContents
        );
    }, [selectedTemplate, title, authors, sectionContents, showLatex, manualLatex, allSections]);

    // Sync generated latex to manual editor when switching modes
    const handleToggleLatex = useCallback(() => {
        if (!showLatex) {
            setManualLatex(latexSource);
        }
        setShowLatex((prev) => !prev);
    }, [showLatex, latexSource]);

    const handleSectionChange = useCallback((id: string, value: string) => {
        setSectionContents((prev) => ({ ...prev, [id]: value }));
    }, []);

    const handleAddSection = useCallback(() => {
        const id = `custom-${Date.now()}`;
        const newSection: SectionDef = {
            id,
            label: "New Section",
            placeholder: "Write your content here…",
        };
        setCustomSections((prev) => [...prev, newSection]);
        setActiveSection(id);
    }, []);

    const handleRenameSectionLabel = useCallback((id: string, label: string) => {
        setCustomSections((prev) =>
            prev.map((s) => (s.id === id ? { ...s, label } : s))
        );
    }, []);

    const handleRemoveSection = useCallback((id: string) => {
        setCustomSections((prev) => prev.filter((s) => s.id !== id));
        setSectionContents((prev) => {
            const next = { ...prev };
            delete next[id];
            return next;
        });
    }, []);

    // Simulated AI generation
    const handleAiGenerate = useCallback((sectionId: string) => {
        setAiLoading(sectionId);
        setTimeout(() => {
            const aiResponses: Record<string, string> = {
                abstract:
                    "This paper presents a novel approach to the research problem. We introduce a framework that addresses key limitations of existing methods. Our experimental results demonstrate significant improvements across multiple evaluation metrics, with an average performance gain of 12.3% over state-of-the-art baselines. The proposed method is computationally efficient and generalizes well to unseen data distributions.",
                intro:
                    "The rapid advancement of technology has created new opportunities and challenges in this research area. Despite significant progress in recent years, several fundamental problems remain unsolved. Existing approaches suffer from limitations including scalability issues, poor generalization, and high computational costs.\n\nIn this paper, we address these challenges by proposing a new methodology that combines insights from multiple disciplines. Our key contributions are:\n\n1. A novel framework that unifies previously disparate approaches\n2. A comprehensive evaluation on standard benchmarks\n3. Theoretical analysis providing convergence guarantees",
                method:
                    "Our proposed approach consists of three main components. First, we preprocess the input data using a standardized pipeline to ensure consistency. Second, we apply our core algorithm, which operates in two phases: an initial estimation step followed by an iterative refinement procedure. Third, we employ a post-processing module that filters and validates the outputs.\n\nThe algorithm's time complexity is O(n log n), making it suitable for large-scale applications. We implement our method using Python with NumPy and PyTorch libraries.",
                results:
                    "We evaluate our approach on three benchmark datasets. On Dataset A, our method achieves an accuracy of 94.7%, compared to 91.2% for the best baseline. On Dataset B, we observe a 15% reduction in error rate. The improvement is statistically significant (p < 0.01) across all experiments.\n\nQualitative analysis reveals that our method produces more coherent and consistent outputs, particularly in challenging edge cases where prior methods tend to fail.",
                conclusion:
                    "In this paper, we presented a novel approach that addresses key limitations of existing methods. Our experimental evaluation demonstrates consistent improvements across multiple benchmarks. The proposed framework is both theoretically grounded and practically effective.\n\nFuture work will explore extending our approach to additional domains and investigating the integration of complementary techniques to further improve performance.",
                discussion:
                    "Our results indicate that the proposed approach offers substantial improvements over existing methods. The performance gains are particularly pronounced in scenarios with limited training data, suggesting that our method learns more generalizable representations.\n\nA limitation of our current approach is its reliance on specific preprocessing steps. Future work could explore end-to-end learning to eliminate this dependency.",
            };

            // Match partial section IDs
            const key = Object.keys(aiResponses).find((k) =>
                sectionId.toLowerCase().includes(k)
            );
            const response = key
                ? aiResponses[key]
                : "This section discusses the relevant aspects of the research. Further analysis and detailed elaboration will strengthen the argumentation and provide comprehensive coverage of the topic.";

            setSectionContents((prev) => ({
                ...prev,
                [sectionId]: (prev[sectionId] || "") + (prev[sectionId] ? "\n\n" : "") + response,
            }));
            setAiLoading(null);
        }, 1500);
    }, []);

    /* ── Template Picker ── */
    if (!selectedTemplate) {
        return (
            <div className={styles.templatePicker}>
                <div className={styles.templateHeader}>
                    <h1>Start a New Paper</h1>
                    <p>Choose a template to get started. You can always customize the structure later.</p>
                </div>
                <div className={styles.templateGrid}>
                    {TEMPLATES.map((t) => (
                        <button
                            key={t.id}
                            className={styles.templateCard}
                            onClick={() => {
                                setSelectedTemplate(t);
                                setActiveSection(t.sections[0]?.id || null);
                            }}
                        >
                            <span className={styles.templateIcon}>{t.icon}</span>
                            <span className={styles.templateName}>{t.name}</span>
                            <span className={styles.templateDesc}>{t.description}</span>
                            <span className={styles.templateSections}>
                                {t.sections.length} sections
                            </span>
                        </button>
                    ))}
                </div>
            </div>
        );
    }

    /* ── Editor ── */
    return (
        <div className={styles.editorPage}>
            {/* Toolbar */}
            <div className={styles.toolbar}>
                <div className={styles.toolbarLeft}>
                    <button
                        className={`btn btn-ghost ${styles.backBtn}`}
                        onClick={() => setSelectedTemplate(null)}
                    >
                        ← Templates
                    </button>
                    <span className={styles.templateBadge}>
                        {selectedTemplate.icon} {selectedTemplate.name}
                    </span>
                </div>
                <div className={styles.toolbarRight}>
                    <button
                        className={`btn ${showLatex ? "btn-primary" : "btn-secondary"} ${styles.toggleBtn}`}
                        onClick={handleToggleLatex}
                    >
                        {showLatex ? "◈ Simple Mode" : "{ } LaTeX Mode"}
                    </button>
                    <button className="btn btn-ghost">⬇ Export</button>
                    <button className="btn btn-ghost">📋 PDF</button>
                </div>
            </div>

            <div className={styles.splitPane}>
                {/* Left: Input */}
                <div className={styles.inputPane}>
                    {showLatex ? (
                        /* LaTeX Editor */
                        <div className={styles.latexEditor}>
                            <div className={styles.paneLabel}>LaTeX Source</div>
                            <textarea
                                className={styles.latexTextarea}
                                value={manualLatex}
                                onChange={(e) => setManualLatex(e.target.value)}
                                spellCheck={false}
                            />
                        </div>
                    ) : (
                        /* Simple Mode */
                        <div className={styles.simpleEditor}>
                            {/* Meta fields */}
                            <div className={styles.metaFields}>
                                <div className={styles.field}>
                                    <label className={styles.fieldLabel}>Paper Title</label>
                                    <input
                                        type="text"
                                        className={`input ${styles.titleInput}`}
                                        placeholder="Enter the title of your paper…"
                                        value={title}
                                        onChange={(e) => setTitle(e.target.value)}
                                    />
                                </div>
                                <div className={styles.field}>
                                    <label className={styles.fieldLabel}>Authors</label>
                                    <input
                                        type="text"
                                        className="input"
                                        placeholder="e.g. Jane Smith, Alex Chen"
                                        value={authors}
                                        onChange={(e) => setAuthors(e.target.value)}
                                    />
                                </div>
                            </div>

                            {/* Section List */}
                            <div className={styles.sectionList}>
                                <div className={styles.sectionListHeader}>
                                    <span className={styles.paneLabel}>Sections</span>
                                    <button
                                        className={`btn btn-ghost ${styles.addBtn}`}
                                        onClick={handleAddSection}
                                    >
                                        + Add Section
                                    </button>
                                </div>

                                {allSections.map((sec, idx) => {
                                    const isActive = activeSection === sec.id;
                                    const isCustom = sec.id.startsWith("custom-");
                                    return (
                                        <div
                                            key={sec.id}
                                            className={`${styles.sectionBlock} ${isActive ? styles.sectionActive : ""}`}
                                        >
                                            <button
                                                className={styles.sectionHeader}
                                                onClick={() =>
                                                    setActiveSection(isActive ? null : sec.id)
                                                }
                                            >
                                                <span className={styles.sectionNum}>{idx + 1}</span>
                                                {isCustom && isActive ? (
                                                    <input
                                                        type="text"
                                                        className={styles.sectionRename}
                                                        value={sec.label}
                                                        onClick={(e) => e.stopPropagation()}
                                                        onChange={(e) =>
                                                            handleRenameSectionLabel(sec.id, e.target.value)
                                                        }
                                                    />
                                                ) : (
                                                    <span className={styles.sectionLabel}>
                                                        {sec.label}
                                                    </span>
                                                )}
                                                <span className={styles.sectionStatus}>
                                                    {sectionContents[sec.id]
                                                        ? `${sectionContents[sec.id].split(/\s+/).filter(Boolean).length} words`
                                                        : "Empty"}
                                                </span>
                                                <span className={styles.chevron}>
                                                    {isActive ? "▾" : "▸"}
                                                </span>
                                            </button>

                                            {isActive && (
                                                <div className={styles.sectionBody}>
                                                    <textarea
                                                        className={styles.sectionTextarea}
                                                        placeholder={sec.placeholder}
                                                        value={sectionContents[sec.id] || ""}
                                                        onChange={(e) =>
                                                            handleSectionChange(sec.id, e.target.value)
                                                        }
                                                        rows={8}
                                                    />
                                                    <div className={styles.sectionActions}>
                                                        <button
                                                            className={`btn btn-secondary ${styles.aiBtn}`}
                                                            onClick={() => handleAiGenerate(sec.id)}
                                                            disabled={aiLoading === sec.id}
                                                        >
                                                            {aiLoading === sec.id ? (
                                                                <>⏳ Generating…</>
                                                            ) : (
                                                                <>✨ AI Generate</>
                                                            )}
                                                        </button>
                                                        <button
                                                            className={`btn btn-ghost ${styles.aiBtn}`}
                                                            onClick={() => handleAiGenerate(sec.id)}
                                                            disabled={aiLoading === sec.id}
                                                        >
                                                            🔄 AI Improve
                                                        </button>
                                                        {isCustom && (
                                                            <button
                                                                className="btn btn-ghost"
                                                                onClick={() => handleRemoveSection(sec.id)}
                                                                style={{ marginLeft: "auto", color: "#c00" }}
                                                            >
                                                                🗑 Remove
                                                            </button>
                                                        )}
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}
                </div>

                {/* Divider */}
                <div className={styles.divider} />

                {/* Right: Preview */}
                <div className={styles.previewPane}>
                    <div className={styles.paneHeader}>
                        <span>Paper Preview</span>
                    </div>
                    <LatexPreview source={latexSource} templateId={selectedTemplate.id} />
                </div>
            </div>
        </div>
    );
}
