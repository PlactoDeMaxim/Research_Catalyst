# Research Catalyst — Architecture & Technical Overview

This document provides a comprehensive overview of the **Research Catalyst** platform. It details how the project is structured, how the frontend and backend communicate, and how each individual module operates to assist researchers in their workflows.

---

## 1. High-Level Architecture

Research Catalyst is built as a modern web application consisting of two primary tiers:
1. **Frontend**: A [Next.js](https://nextjs.org/) (App Router) application built with React and TypeScript, running on Node.js.
2. **Backend**: A [FastAPI](https://fastapi.tiangolo.com/) microservice built with Python, serving as the core engine for data fetching, processing, AI tasks, and domain logic.
3. **Database**: A PostgreSQL database managed via the [Prisma](https://www.prisma.io/) ORM.

Communication between the frontend and backend happens via standard RESTful JSON APIs. The backend runs on port `8000` while the frontend runs on port `3000`.

---

## 2. Frontend Architecture (Next.js)

The frontend uses the Next.js App Router (`src/app`) for routing and server/client components. It is designed to be deeply modular so that different modules can be developed independently.

### Folder Structure
- **`src/app/`**: Contains the page routes.
  - `/discovery`: The paper search and discovery interface.
  - `/planner`: The project and milestone management interface.
  - `/visualize`: The diagram and chart generation interface.
  - `/editor`: The document writing and LaTeX preview interface.
- **`src/modules/`**: Contains the business logic, hooks, and localized components for specific functional areas (e.g., `discovery`, `planner`, `visualize`, `writing`, `citations`). This strict separation allows multiple developers to work without merge conflicts.
- **`src/components/`**: Contains globally shared UI components (e.g., `Sidebar`, `LatexPreview`).

### Data Flow
Frontend pages use React Client Components (`"use client"`) to manage state and fetch data directly from the FastAPI backend (e.g., calling `http://localhost:8000/api/...`).

---

## 3. Backend Architecture (FastAPI)

The backend is built with modularity in mind. The `main.py` file acts as the entry point, mounting individual routers from the `modules/` directory and handling CORS rules allowing the Next.js frontend to communicate securely.

### Folder Structure
```text
backend/
├── main.py
├── requirements.txt
└── modules/
    ├── paper_search/
    ├── planner/
    └── visualization/
```

Every backend module follows a strict internal pattern:
1. **`routes/`**: FastAPI `APIRouter` definitions (the API surface).
2. **`services/`**: Core business logic and external integrations.
3. **`models/`**: Pydantic schemas for request/response validation.

### Module Breakdown

#### A. Paper Search Module (`backend/modules/paper_search`)
Responsible for fetching and parsing academic papers.
- **Routes (`/api/papers/search`)**: Accepts a query, date ranges, and open-access filters to return a unified list of papers.
- **Services**:
  - `search_service.py`: Orchestrates parallel queries to diverse academic engines (OpenAlex, arXiv, Crossref, Semantic Scholar).
  - `normalization_service.py`: Converts differing API responses into a single common format.
  - `deduplication_service.py`: Merges identical papers returned by multiple sources.
  - `ranking_service.py`: Orders results based on relevance, citation count, and recency.
  - `cache_service.py`: Caches results to reduce rate-limiting and improve latency.

#### B. Planner Module (`backend/modules/planner`)
Handles the management of a user's research project and timeline.
- **Routes (`/api/planner/projects`, etc.)**: CRUD operations for projects and milestones.
- **Services**:
  - `project_store.py`: Interacts with the data layer to persist project state.
  - `rule_engine.py`: A domain-specific engine that automatically generates research plans, phases, and milestones based on topic, domain, and deadlines.

#### C. Visualization Module (`backend/modules/visualization`)
Generates rich diagrams and charts from data or AI prompts.
- **Routes (`/api/visualization/...`)**: Endpoints to render diagrams, generate charts, export to PDF/PNG, and use AI to convert text/code to visual diagrams.
- **Services**:
  - `mermaid_service.py` & `graphviz_render_service.py`: Process diagram definitions and render them (e.g., DOT to SVG).
  - `plotly_chart_service.py`: Takes structured numeric data and builds interactive Plotly JSON payloads.
  - `ai_diagram_service.py` & `llm_provider.py`: Connects to LLMs to parse unstructured research text or source code and automatically write diagram definitions (like Mermaid graphs).
  - `export_service.py`: Converts SVG output into downloadable files (PNG/PDF).

---

## 4. Database Schema (Prisma)

The application state is persisted in a relational database (PostgreSQL), strictly typed via Prisma (`prisma/schema.prisma`).

Key Entities:
1. **`Project`**: The core root entity. Represents a user's research endeavor. Has a standard status (`PLANNING`, `LITERATURE_REVIEW`, `WRITING`, `REVIEW`, `COMPLETE`).
2. **`Paper`**: Saved academic papers attached to a Project.
3. **`Milestone`**: Checkpoints and deadlines created by the Planner module's rule engine.
4. **`PaperSection`**: Text chunks representing the document being written (Abstract, Introduction, etc.).
5. **`Citation`**: Stored references in CSL-JSON format to be dynamically injected into the manuscript.

---

## Summary of the Full User Journey

1. **Discovery**: A user searches for papers on the Next.js `/discovery` page. The backend `paper_search` module parallel-fetches across 4 databases, deduplicates, and returns the top results.
2. **Planning**: The user creates a `Project` on the `/planner` page. The backend `planner` module's rule engine generates a custom timeline with specific `Milestone`s.
3. **Extraction & Visualization**: The user analyzes paper methodology or code. The Next.js `/visualize` page calls the backend `visualization` AI services to automatically generate system architecture diagrams or data charts.
4. **Writing**: The user compiles everything in the `/editor` page, writing `PaperSection`s, adding `Citation`s, and previewing the final LaTeX output via the `LatexPreview` component. Default states and interactions are tracked persistently in PostgreSQL via Prisma.
