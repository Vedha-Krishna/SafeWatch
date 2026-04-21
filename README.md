## HORNY_APPLE Monorepo

### Backend (Python + FastAPI + Agents)

Python code now lives fully under `backend/`:

- `backend/main.py` FastAPI API entrypoint
- `backend/agents/crawler/` deterministic crawler logic
- `backend/agents/langchain/` Classifier/Decider/Cleaner workflow
- `backend/db/` database utilities (Supabase client helper)
- `backend/requirements.txt` Python dependencies
- `backend/.venv/` Python virtual environment

Input data: `data/sample_posts.json`  
Crawler output: `data/incident_drafts.json`

Create environment and install dependencies:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

Run API (from repo root):

```bash
python3 -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Run API (from `backend/`):

```bash
python3 -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

API docs:
- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/api/incidents?candidate_only=true`

### Frontend (Next.js App Router)

Install and run:

```bash
cd frontend
npm install
npm run dev
```

Build check:

```bash
npm run build
```

### Run Full Stack

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
