# Research Catalyst Backend — Modular Reference (Review / Deep Dive)

This document maps **how the backend works** and **what each module contains**, so you can answer reviewer questions. Paths are relative to `research-catalyst/backend/`.

---

## 1. Entry point and configuration

**File:** `main.py`

- Builds the FastAPI app (`title`: Research Catalyst Backend).
- **Env loading**: `load_dotenv(backend/.env)` then project-root `.env` (non-overriding), so local backend settings can override root.
- **CORS**: `CORS_ORIGINS` env var (comma-separated); default includes `http://localhost:3000` for Next.js.
- **Routers** (each `include_router` with a prefix):

  | Prefix | Router module |
  |--------|----------------|
  | `/api/papers` | `modules.paper_search.routes.search_routes` |
  | `/api/visualization` | `modules.visualization.routes.visualization_routes` |
  | `/api/planner` | `modules.planner.routes.planner_routes` |
  | `/api/summary` | `modules.summary.routes.summary_routes` |
  | `/api/paper-editor` | `modules.paper_editor.routes.paper_editor_routes` |
  | `/api/code-mapper` | `modules.code_mapper.routes.code_mapper_routes` |
  | `/api/plagiarism-check` | `modules.plagiarism_check.routes.plagiarism_routes` |
  | `/api/citation-manager` | `modules.citation_manager.routes.citation_manager_routes` |
  | `/api/core` | `modules.core.routes.core_routes` |
  | `/api/multi-research` | `modules.multi_research.routes.multi_research_routes` |

- **Health**: `GET /health` — liveness check.

**Dependencies:** see `requirements.txt` (FastAPI, Uvicorn, Pydantic, httpx, psycopg, CrewAI, visualization libs, etc.).

---

## 2. Shared infrastructure — `modules/core/`

**Role:** Backbone for projects, evidence, LLM gateway, retrieval, tasks, and optional PostgreSQL.

### 2.1 `postgres_store.py`

- If `DATABASE_URL` is set **and** `psycopg` imports, `database_enabled()` is true.
- Normalizes Prisma-style URLs (strips `?schema=public` for psycopg).
- Implements workspace projects (planner, editor, general kinds), documents, milestones, editor state, and related CRUD used by planner, evidence registry, and editor routes.

### 2.2 `evidence_registry.py`

- **Canonical model**: research projects, documents, evidence chunks, claims.
- When DB is off: **in-memory** dicts; when on: persists via `postgres_store`.

### 2.3 `model_gateway.py`

- Central **LLM generation** used by `/api/core/model-gateway/generate` (`GatewayRequest` → `generate(req)`).

### 2.4 `prompt_registry.py`

- Template listing for tasks: `/api/core/prompts?task_type=...`.

### 2.5 `retrieval_service.py`

- Ingest text documents and search: `/api/core/retrieval/ingest`, `/api/core/retrieval/search`.

### 2.6 `job_bus.py`

- Workspace task lifecycle: `POST /api/core/tasks`, `GET /api/core/tasks`.

### 2.7 `object_store.py`

- Used by plagiarism (and similar) to save uploaded bytes or text artifacts to storage paths.

### 2.8 `core_routes.py` — quick endpoint map

- `GET /capabilities` — feature list for the core module.
- `POST/GET /projects`, documents, evidence chunks, claims — evidence backbone.
- `POST /model-gateway/generate`, `GET /prompts`.
- `POST /retrieval/ingest`, `GET /retrieval/search`.
- `POST/GET /tasks`.
- `GET/POST/PUT/DELETE /editor-projects` — editor workspace persistence when DB enabled.

**Review tip:** Explain that **core** is the integration layer for a **canonical research project + evidence** model and **optional Postgres**, while feature modules stay focused on UX-facing workflows.

---

## 3. Paper search — `modules/paper_search/`

**Route:** `GET /api/papers/search`

**Flow (`services/search_service.py`):**

1. Check **cache** (24h) for same query + filters.
2. **Parallel** calls: OpenAlex, arXiv, Crossref, Semantic Scholar (failures tolerated per provider).
3. **Merge** → **deduplicate** → optional OA filter → **rank** (citations, recency, OA).
4. Cache result → return `SearchResponse`.

**Supporting pieces:** `providers/*`, `deduplication_service`, `ranking_service`, `cache_service`, `models/paper_model.py`.

---

## 4. Visualization — `modules/visualization/`

**Routes (all under `/api/visualization`):**

- `POST /diagram/generate`, `/diagram/render` — Graphviz DOT → SVG; Mermaid validated and returned for frontend rendering.
- `POST /chart/generate` — Plotly charts from structured data.
- `POST /export` — SVG to PNG/PDF via Kaleido/export service.
- `POST /ai/text-to-diagram`, `/ai/code-to-diagram` — LLM-based diagram generation.

**Services:** `diagram_generation_service`, `graphviz_render_service`, `mermaid_service`, `plotly_chart_service`, `export_service`, `ai_diagram_service`.

---

## 5. Planner — `modules/planner/`

**Routes:** `/api/planner/projects`, milestones, `POST .../generate` for plan generation.

**`project_store.py`:**

- **Postgres**: lists/creates projects `kind="planner"` with milestones from DB.
- **Fallback**: in-memory `_projects` dict.
- Plan generation uses **`rule_engine`** and **`llm_engine`** (`generate_plan`, `generate_plan_with_llm`).

---

## 6. Summary discovery — `modules/summary/`

**Data:** `paper_service.py` loads **`parsed_papers.json`** from the workspace (searched upward from the module path) — categories, list/search, detail by slug.

**Notable routes (`summary_routes.py`):**

- `GET /categories`, `/papers`, `/papers/search`, `/papers/{slug}`.
- **Workspace**: `POST /workspace/chat`, `/workspace/synthesize`, `/workspace/extract-table`, `/workspace/gap-analysis`.
- **Collections** and **screening** sessions/entries (PRISMA-style workflow).
- `POST /upload` — PDF only; **`pdf_summarizer`** extracts text and summarizes; **`register_uploaded_paper`** adds to in-memory store.
- `GET /uploaded` — list uploaded summaries.

**Services:** `paper_service`, `workspace_service`, `pdf_summarizer`.

---

## 7. Paper editor — `modules/paper_editor/`

**LaTeX workflow:**

- Upload **ZIP** template → workspace under `template_service` (`BASE_WORK_DIR`).
- **Inject** generated sections into `.tex` (`injection_service`).
- **Compile** via background job (`compile_service.enqueue_compile_job`) — status and logs in `job_store`; **PDF download** when ready.
- **V2** `compile-source` creates workspace from file payload.

**Writing assistant (`writing_assistant_service`):** grounded draft, autocomplete, citation recommendations, claim trace, manuscript review, reviewer response plan, compliance check, unified `assist`.

**Diagnostics:** `_extract_diagnostics` parses pdflatex logs for structured errors.

---

## 8. Code mapper — `modules/code_mapper/`

### Paper → code

- `POST /paper-to-code/upload` — saves temp file, **`job_manager.create_job`**, background pipeline:
  - `parse_document` → `extract_methodology` (LLM) → `generate_blueprint` → `generate_all_files` → `validate_and_fix` → `package_project` (ZIP).
- `GET` status, **SSE** stream, result, **ZIP download**.

### Repo → paper

- `POST /repo-to-paper/analyze` — clone/analyze GitHub repo → **`generate_report`** → export LaTeX and/or Word.
- Section updates **`PUT /repo-to-paper/sections/{job_id}`** re-export LaTeX/Word and refresh job result.
- Download LaTeX (as ZIP) or Word.

**Utilities:** `llm_client.chat` for LLM; `test-llm` endpoint for configuration checks.

---

## 9. Plagiarism check — `modules/plagiarism_check/`

**MVP strategy:** overlap against **retrieved scholarly abstracts** (OpenAlex / Semantic Scholar–style flow inside `mvp_plagiarism_service`), not full-web indexing.

- `POST /scan/text`, `/scan/file` — create job in `plagiarism_store`, store artifacts via **`object_store`**, return `ScanJob` with summary + section findings + alerts.

---

## 10. Citation manager — `modules/citation_manager/`

- **Projects** and **citations** CRUD via `citation_store` (in-memory or backed — check `citation_store.py` for persistence rules).
- **`POST /generate`** — `citation_generation_service.generate_citation(source, format)`.

---

## 11. Multi-agent research — `modules/multi_research/`

**Orchestration:** `services/pipeline.py` — **CrewAI** `Crew` with sequential process.

- **Agents:** planner, search, validator, extractor, synthesizer (`services/agents/*`).
- **Tasks:** planning, search, validation, extraction, summary (`tasks/*`).
- **LLM:** `_build_llm()` uses **Ollama** via CrewAI (`OLLAMA_API_KEY`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `LLM_TEMPERATURE`).

**Routes:**

- `POST /api/multi-research/run` — **SSE** (`EventSourceResponse`); worker thread runs `run_research_pipeline` with progress callbacks.
- `POST /api/multi-research/run-sync` — synchronous full report (Markdown string).

**Tools:** `tools/web_parser.py`, `pdf_extractor.py`, `search_tool.py`; **utils:** chunking, tokens.

---

## 12. Cross-cutting concerns

| Topic | Where |
|--------|--------|
| Auth | This backend is primarily **API + CORS**; user auth may live in frontend or another service — confirm for your deployment story. |
| File limits | Summary PDF upload max **50MB**; plagiarism max **15MB**; file types enforced per route. |
| Errors | Routes generally catch exceptions and return **HTTPException** with 4xx/5xx and message. |
| Idempotency | Search uses **cache**; jobs use **UUID** job IDs where applicable. |

---

## 13. Likely reviewer Q&A (short)

**Q: How is data persisted?**  
A: **PostgreSQL** when `DATABASE_URL` is set (`postgres_store`); otherwise several modules use **in-memory** stores (planner fallback, uploaded papers in summary, some citation/plagiarism state — verify per `*_store.py`).

**Q: How does paper search work?**  
A: Parallel external APIs → merge → dedupe → rank → cache.

**Q: What runs multi-agent research?**  
A: CrewAI + Ollama-configured LLM in `pipeline.py`; SSE for streaming progress.

**Q: How does the paper editor compile PDF?**  
A: Async compile jobs, logs, artifact path, download endpoint; template inject then `pdflatex`/toolchain (see `compile_service`).

**Q: What is “core” for?**  
A: Shared backbone: evidence-linked projects, retrieval, model gateway, editor projects in DB when enabled.

---

*Generated from repository analysis. For exact endpoint lists, use FastAPI’s interactive docs at `/docs` when the server is running.*
