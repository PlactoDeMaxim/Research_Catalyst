# Plagiarism Detection Module

**Phase:** 4 — Quality and Review Systems  
**Owner:** _Unclaimed_  
**Status:** 🔲 Not Started

## Purpose
Detects text similarity, identifies potential plagiarism, and suggests corrections or paraphrasing alternatives.

## Key Features
- Similarity detection against academic databases
- Section-level plagiarism highlighting
- Safe paraphrasing suggestions
- Originality score (≥ 95% target accuracy)

## API Contract
```
POST /api/plagiarism/check      { content, projectId }
GET  /api/plagiarism/report     { projectId }
POST /api/plagiarism/paraphrase { text }
```

## Dependencies
- Shared: `src/lib/prisma.ts`
