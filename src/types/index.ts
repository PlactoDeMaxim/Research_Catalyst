// Shared types for the Research Catalyst platform
// Contributors: import from '@/types' for shared interfaces

export type ProjectStatus =
    | "PLANNING"
    | "LITERATURE_REVIEW"
    | "WRITING"
    | "REVIEW"
    | "COMPLETE";

export type SectionType =
    | "ABSTRACT"
    | "INTRODUCTION"
    | "METHODOLOGY"
    | "RESULTS"
    | "CONCLUSION";

export interface Project {
    id: string;
    title: string;
    description: string;
    status: ProjectStatus;
    createdAt: string;
    updatedAt: string;
}

export interface Paper {
    id: string;
    title: string;
    authors: string;
    abstract: string;
    url: string;
    projectId: string;
    createdAt: string;
}

export interface PaperSection {
    id: string;
    sectionType: SectionType;
    content: string;
    order: number;
    projectId: string;
    createdAt: string;
    updatedAt: string;
}

export interface Milestone {
    id: string;
    title: string;
    description: string;
    dueDate: string | null;
    completed: boolean;
    projectId: string;
    createdAt: string;
}

export interface Citation {
    id: string;
    citationText: string;
    cslJson: string;
    projectId: string;
    createdAt: string;
}
