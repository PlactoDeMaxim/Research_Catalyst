# How to Run Research Catalyst

This project can run **locally** with Node + Python, or via **Docker** for a more isolated setup.

---

## 1. Prerequisites

- **Node.js** v18+ (LTS recommended)
- **Python** 3.10+
- **Graphviz** (for diagram rendering in the backend)  
  - Windows: `winget install Graphviz.Graphviz`
- **Docker** + Docker Desktop (for containerized runs)

---

## 2. Running with Docker (recommended for full stack)

From the repo root (`research-catalyst/`):

```bash
# 1) Build images (backend + frontend)
docker compose build

# 2) Start everything (FastAPI + Next.js + any sidecars)
docker compose up
```

Then open:

| Service | URL (default) |
|---------|---------------|
| Frontend (web app) | http://localhost:3000 |
| Backend API docs | http://localhost:8000/docs |

> If ports are already in use, adjust them in `docker-compose.yml` and re-run `docker compose up`.

To stop:

```bash
docker compose down
```

---

## 3. Running locally without Docker

### 3.1 Backend (FastAPI)

```bash
cd research-catalyst/backend
python -m venv .venv
.venv\Scripts\activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Make sure backend/.env is configured (CORS_ORIGINS, OLLAMA_*, etc.)
python -m uvicorn main:app --reload --port 8000
```

### 3.2 Frontend (Next.js)

In a separate terminal:

```bash
cd research-catalyst
npm install
npm run dev
```

The frontend talks to the backend via the built-in proxy routes (e.g. `/api/paper-editor-proxy`) which default to `http://127.0.0.1:8000`. If your backend runs elsewhere, set the appropriate `NEXT_PUBLIC_*` env vars in `.env.local`.

---

## 4. Access URLs

When running either via Docker or locally:

| Page | URL |
|------|-----|
| Home | http://localhost:3000 |
| Paper Discovery | http://localhost:3000/discovery |
| Research Planner | http://localhost:3000/planner |
| Visualization Studio | http://localhost:3000/visualize |
| Paper Editor (v2) | http://localhost:3000/editor-v2 |
| API Docs (FastAPI) | http://localhost:8000/docs |

