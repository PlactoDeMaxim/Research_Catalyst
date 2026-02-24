# Research Catalyst — Module Structure

Each module below is **self-contained** so different contributors can work independently without merge conflicts.

## Folder Convention

Every module follows this structure:

```
modules/<module-name>/
├── README.md           ← Module overview, API contracts, owner
├── components/         ← React components specific to this module
├── hooks/              ← Custom React hooks
├── services/           ← API call functions / business logic
├── types/              ← TypeScript interfaces and types
├── utils/              ← Helper functions
└── __tests__/          ← Unit and integration tests
```

The corresponding **API routes** live in:
```
src/app/api/<module-name>/route.ts
```

And the **page** (if any) lives in:
```
src/app/<module-name>/page.tsx
```

## Module Registry

| # | Module | Folder | Phase | Status |
|---|--------|--------|-------|--------|
| 1 | Paper Discovery | `modules/discovery/` | Phase 2 | 🔲 Not Started |
| 2 | Writing Assistant | `modules/writing/` | Phase 2 | 🔲 Not Started |
| 3 | Code-Paper Mapper | `modules/code-mapper/` | Phase 3 | 🔲 Not Started |
| 4 | Visualization Generator | `modules/visualize/` | Phase 3 | 🔲 Not Started |
| 5 | Paper Scoring Engine | `modules/scoring/` | Phase 4 | 🔲 Not Started |
| 6 | Plagiarism Detection | `modules/plagiarism/` | Phase 4 | 🔲 Not Started |
| 7 | Summarization | `modules/summarizer/` | Phase 2 | 🔲 Not Started |
| 8 | Research Planner | `modules/planner/` | Phase 2 | 🔲 Not Started |
| 9 | Citation Management | `modules/citations/` | Phase 3 | 🔲 Not Started |

## Contributing

1. Claim a module by adding your name in the module's `README.md`
2. Work exclusively within your module folder + its API route + its page
3. Shared types go in `src/types/` — coordinate with other contributors
4. Shared components go in `src/components/` — discuss before adding
