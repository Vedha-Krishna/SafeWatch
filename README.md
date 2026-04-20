## Sathish Sugheetha Vedha Krishna

## Required Libraries
```bash
python3 -m pip install -r requirements.txt
```

Input: `data/sample_posts.json`

Output: `data/incident_drafts.json`

## Backend (FastAPI)

Run from repo root:

```bash
python3 -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

API docs:
- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/api/incidents?candidate_only=true`

## Frontend (Next.js + React + TypeScript)

Install and run:

```bash
cd frontend
npm install
npm run dev
```

Optional env override:

```bash
cp .env.local.example .env.local
```

Build check:

```bash
npm run build
```

If your environment blocks Turbopack process spawning, use:

```bash
npm run build -- --webpack
```

## Run Full Stack

1. Start backend:
```bash
python3 -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```
2. In another terminal start frontend:
```bash
cd frontend
npm run dev
```
3. Open `http://localhost:3000`
