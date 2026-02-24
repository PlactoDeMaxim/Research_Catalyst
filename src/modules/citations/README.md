# Citation Management Module

**Phase:** 3 — Advanced Research Assistance  
**Owner:** _Unclaimed_  
**Status:** 🔲 Not Started

## Purpose
Automatically generates, formats, and manages citations and references for research papers.

## Key Features
- Auto-generate citations from URLs or DOIs
- Multiple citation formats (APA, MLA, IEEE, Chicago)
- In-text citation insertion
- Bibliography management
- CSL JSON support

## API Contract
```
GET    /api/citations?projectId=<id>
POST   /api/citations         { citationText, cslJson, projectId }
POST   /api/citations/from-url { url, format }
DELETE /api/citations/:id
```

## Dependencies
- Shared: `src/lib/prisma.ts`, Citation model
- Page: `src/app/editor/page.tsx` (citations panel already scaffolded)
