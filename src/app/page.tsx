import styles from "./page.module.css";
import Link from "next/link";

const mockProjects = [
    {
        id: "1",
        title: "Deep Learning for Medical Image Segmentation",
        description:
            "Exploring U-Net architectures for automated tumor detection in MRI scans",
        status: "WRITING",
        updatedAt: "2 hours ago",
    },
    {
        id: "2",
        title: "Transformer-Based Sentiment Analysis",
        description:
            "Fine-tuning BERT models for multilingual opinion mining across social media",
        status: "LITERATURE_REVIEW",
        updatedAt: "1 day ago",
    },
    {
        id: "3",
        title: "Federated Learning Privacy Framework",
        description:
            "Designing differential privacy mechanisms for distributed model training",
        status: "PLANNING",
        updatedAt: "3 days ago",
    },
];

const statusLabels: Record<string, { label: string; className: string }> = {
    PLANNING: { label: "Planning", className: "badge-planning" },
    LITERATURE_REVIEW: { label: "Literature Review", className: "badge-literature" },
    WRITING: { label: "Writing", className: "badge-writing" },
    REVIEW: { label: "Review", className: "badge-review" },
    COMPLETE: { label: "Complete", className: "badge-complete" },
};

export default function Dashboard() {
    return (
        <div>
            {/* Page Header */}
            <div className={styles.header}>
                <div>
                    <h1>Projects</h1>
                    <p className={styles.subtitle}>
                        Manage your research projects and track progress.
                    </p>
                </div>
                <button className="btn btn-primary">+ New Project</button>
            </div>

            {/* Quick Access */}
            <div className={`grid grid-4 ${styles.quickRow}`}>
                {[
                    { icon: "🔍", label: "Paper Discovery", href: "/discovery" },
                    { icon: "📝", label: "Paper Editor", href: "/editor" },
                    { icon: "📈", label: "Visualization", href: "/visualize" },
                    { icon: "📅", label: "Research Planner", href: "/planner" },
                    { icon: "📚", label: "Citations", href: "/citation-manager" },
                    { icon: "🛡️", label: "Plagiarism Check", href: "/plagiarism-check" },
                ].map((item) => (
                    <Link
                        key={item.href}
                        href={item.href}
                        className={`${styles.quickCard}`}
                    >
                        <span className={styles.quickIcon}>{item.icon}</span>
                        <span className={styles.quickLabel}>{item.label}</span>
                        <span className={styles.quickArrow}>→</span>
                    </Link>
                ))}
            </div>

            {/* Projects List */}
            <div className={styles.section}>
                <h2 className="section-label">Recent Projects</h2>
                <div className={styles.projectList}>
                    {mockProjects.map((project) => (
                        <Link
                            key={project.id}
                            href="/editor"
                            className={`${styles.projectRow} animate-in`}
                        >
                            <div className={styles.projectInfo}>
                                <h3 className={styles.projectTitle}>{project.title}</h3>
                                <p className={styles.projectDesc}>{project.description}</p>
                            </div>
                            <div className={styles.projectMeta}>
                                <span
                                    className={`badge ${statusLabels[project.status]?.className}`}
                                >
                                    {statusLabels[project.status]?.label}
                                </span>
                                <span className={styles.timestamp}>{project.updatedAt}</span>
                            </div>
                        </Link>
                    ))}
                </div>
            </div>
        </div>
    );
}
