# Visualization Generator Module

**Phase:** 3 — Advanced Research Assistance  
**Owner:** _Unclaimed_  
**Status:** 🔲 Not Started

## Purpose
Automatically generates publication-ready diagrams, flowcharts, architecture diagrams, and graphs from methodology descriptions or code.

## Key Features
- Flowchart generation from methodology steps
- Architecture diagram generation
- Sequence diagram support
- Graph/chart generation from data
- Export to PNG, SVG, PDF

## API Contract
```
POST /api/visualize/generate   { input, diagramType }
GET  /api/visualize/gallery    { projectId }
PUT  /api/visualize/:id        { edits }
```

## Dependencies
- Shared: `src/lib/prisma.ts`
- Page: `src/app/visualize/page.tsx` (UI already scaffolded)
