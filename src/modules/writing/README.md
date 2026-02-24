# Writing Assistant Module

**Phase:** 2 — Core Research Modules  
**Owner:** _Unclaimed_  
**Status:** 🔲 Not Started

## Purpose
AI-powered writing assistant that helps generate and improve paper sections (Abstract, Introduction, Methodology, Results, Conclusion).

## Key Features
- Section-by-section drafting with AI
- Grammar and style suggestions
- Academic tone enforcement
- Content improvement recommendations

## API Contract
```
POST /api/writing/generate   { sectionType, prompt, projectId }
POST /api/writing/improve    { sectionId, content }
GET  /api/writing/suggestions { sectionId }
```

## Dependencies
- Shared: `src/lib/prisma.ts`, `prisma/schema.prisma` (PaperSection model)
- Page: `src/app/editor/page.tsx` (UI already scaffolded)
