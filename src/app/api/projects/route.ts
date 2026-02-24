import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

// GET /api/projects — List all projects
export async function GET() {
    try {
        const projects = await prisma.project.findMany({
            orderBy: { updatedAt: "desc" },
            include: {
                _count: {
                    select: {
                        papers: true,
                        sections: true,
                        milestones: true,
                        citations: true,
                    },
                },
            },
        });
        return NextResponse.json(projects);
    } catch (error) {
        console.error("Failed to fetch projects:", error);
        return NextResponse.json(
            { error: "Failed to fetch projects" },
            { status: 500 }
        );
    }
}

// POST /api/projects — Create a new project
export async function POST(request: Request) {
    try {
        const body = await request.json();
        const { title, description } = body;

        if (!title || typeof title !== "string") {
            return NextResponse.json(
                { error: "Title is required" },
                { status: 400 }
            );
        }

        const project = await prisma.project.create({
            data: {
                title,
                description: description || "",
            },
        });

        return NextResponse.json(project, { status: 201 });
    } catch (error) {
        console.error("Failed to create project:", error);
        return NextResponse.json(
            { error: "Failed to create project" },
            { status: 500 }
        );
    }
}
