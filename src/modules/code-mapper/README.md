# Code-Paper Mapper Module

**Phase:** 3 — Advanced Research Assistance  
**Status:** Implemented

## Purpose
Bidirectional mapping between research code and paper methodology — converts papers into runnable implementations and GitHub repositories into academic papers.

## Features

### Feature 1: Paper → Code (AI Research Compiler)
- Upload PDF/Word research paper
- LLM-driven methodology extraction (architecture, training, losses, metrics)
- Multi-phase code generation (blueprint → dependency DAG → sequential file gen)
- AST validation + sandbox execution with self-healing fix loop (up to 5 rounds)
- Download complete project as ZIP with requirements.txt, README, configs

### Feature 2: Repo → Paper (GitHub → Research Paper Generator)
- Shallow-clone and analyze GitHub repositories
- Section-by-section academic paper generation with 2-pass refinement
- Multi-source literature search (OpenAlex, arXiv, Crossref, Semantic Scholar)
- 4-layer citation verification (arXiv ID, DOI, Semantic Scholar title, LLM relevance)
- Export in LaTeX and Word formats

## API Endpoints
```
# Feature 1
POST /api/code-mapper/paper-to-code/upload
GET  /api/code-mapper/paper-to-code/status/{id}
GET  /api/code-mapper/paper-to-code/stream/{id}
GET  /api/code-mapper/paper-to-code/result/{id}
GET  /api/code-mapper/paper-to-code/download/{id}

# Feature 2
POST /api/code-mapper/repo-to-paper/analyze
GET  /api/code-mapper/repo-to-paper/status/{id}
GET  /api/code-mapper/repo-to-paper/stream/{id}
GET  /api/code-mapper/repo-to-paper/result/{id}
GET  /api/code-mapper/repo-to-paper/download/{id}
```

## Frontend Routes
- `/code-mapper` — Landing page
- `/code-mapper/paper-to-code` — Paper upload and code generation
- `/code-mapper/repo-to-paper` — GitHub URL input and paper generation

## Dependencies
- Backend: `PyMuPDF`, `python-docx`, `pyyaml`, `httpx`
- Shared: `src/lib/prisma.ts`
- Reuses: `paper_search` providers, `paper_editor` compile pipeline
