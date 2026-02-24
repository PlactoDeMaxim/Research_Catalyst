# How to Run Research Catalyst

## Prerequisites

- Node.js (v18+)
- Python (3.10+)
- Graphviz (`winget install Graphviz.Graphviz`)

## Backend (FastAPI)

```bash
cd research-catalyst/backend
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

## Frontend (Next.js)

```bash
cd research-catalyst
npm install
npm run dev
```

## Access

| Page | URL |
|------|-----|
| Home | http://localhost:3000 |
| Paper Discovery | http://localhost:3000/discovery |
| Research Planner | http://localhost:3000/planner |
| Visualization Studio | http://localhost:3000/visualize |
| Paper Editor | http://localhost:3000/editor |
| API Docs | http://localhost:8000/docs |
