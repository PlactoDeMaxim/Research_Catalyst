# Summarization Module

**Phase:** 2 — Core Research Modules  
**Owner:** _Unclaimed_  
**Status:** 🔲 Not Started

## Purpose
Provides simplified summaries of research papers and individual sections, making complex research more accessible.

## Key Features
- Full paper summarization
- Section-level summaries
- Key findings extraction
- Adjustable summary length

## API Contract
```
POST /api/summarizer/summarize   { content, length }
POST /api/summarizer/paper       { paperId }
GET  /api/summarizer/keyfindings { paperId }
```

## Dependencies
- Shared: `src/lib/prisma.ts`, Paper model
