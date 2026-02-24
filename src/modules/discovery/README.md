# Discovery Module

**Phase:** 2 — Core Research Modules  
**Owner:** _Unclaimed_  
**Status:** 🔲 Not Started

## Purpose
Finds relevant research papers based on semantic meaning of the user's research problem statement (not just keyword matching).

## Key Features
- Semantic search engine using embeddings
- Paper results ranked by relevance score
- Paper metadata display (title, authors, abstract, citations, year)
- Filter by type (journal, conference, preprint) and year

## API Contract
```
GET  /api/discovery?q=<query>&type=<filter>&year=<filter>
POST /api/discovery/save  { paperId, projectId }
```

## Dependencies
- Shared: `src/lib/prisma.ts`, `prisma/schema.prisma` (Paper model)
- Page: `src/app/discovery/page.tsx` (UI already scaffolded)
