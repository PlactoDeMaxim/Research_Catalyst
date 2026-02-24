# Code-Paper Mapper Module

**Phase:** 3 — Advanced Research Assistance  
**Owner:** _Unclaimed_  
**Status:** 🔲 Not Started

## Purpose
Bidirectional mapping between research code and paper methodology— converts code into methodology descriptions and vice versa.

## Key Features
- Code → methodology description generation
- Methodology text → pseudocode generation
- Inline code annotations linked to paper sections
- Repository upload and analysis

## API Contract
```
POST /api/code-mapper/code-to-text   { code, language }
POST /api/code-mapper/text-to-code   { methodology }
POST /api/code-mapper/upload         multipart/form-data
```

## Dependencies
- Shared: `src/lib/prisma.ts`
