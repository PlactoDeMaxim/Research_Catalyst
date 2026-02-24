# Research Planner Module

**Phase:** 2 — Core Research Modules  
**Owner:** _Unclaimed_  
**Status:** 🔲 Not Started

## Purpose
Creates structured timelines and milestones for completing research, helping researchers track progress through the lifecycle.

## Key Features
- Milestone creation and tracking
- Timeline visualization
- Due date reminders
- Auto-generated research plan from project scope

## API Contract
```
GET    /api/planner/milestones?projectId=<id>
POST   /api/planner/milestones  { title, description, dueDate, projectId }
PUT    /api/planner/milestones/:id  { completed, title, ... }
DELETE /api/planner/milestones/:id
```

## Dependencies
- Shared: `src/lib/prisma.ts`, Milestone model
- Page: `src/app/planner/page.tsx` (UI already scaffolded)
