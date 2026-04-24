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

### Scheduled Pipeline With Vercel Cron

The project includes a Vercel cron route that can trigger the backend pipeline once
per day:

- Vercel calls `frontend/src/app/api/cron/safewatch/route.ts`
- The route validates `CRON_SECRET`
- It calls the backend `GET /api/cron/safewatch`
- The backend runs crawler -> cleaner -> process_incidents/classifier/decider

Setup details are in [`docs/VERCEL_CRON.md`](docs/VERCEL_CRON.md).

---

## Tech Stack

| Layer | Tool |
|---|---|
| Language | Python 3 · TypeScript |
| Backend Framework | FastAPI |
| Agent Orchestration | LangGraph |
| LLM | OpenAI GPT-4o-mini |
| Embeddings | OpenAI text-embedding-3-small |
| Database | Supabase (PostgreSQL) |
| Frontend Framework | Next.js 16 (App Router) |
| Map Library | React-Leaflet |
| UI State | Zustand |

---

## Repository Structure

```
HORNY_APPLE/
├── .env.example
├── README.md
├── graph.png
├── backend/
│   ├── main.py
│   ├── orchestration.py
│   ├── requirements.txt
│   ├── agents/
│   │   ├── cleaner/
│   │   │   └── cleaner_agent.py
│   │   ├── crawler/
│   │   │   ├── deterministic.py
│   │   │   ├── reddit_crawler.py
│   │   │   ├── multimodal.py
│   │   │   ├── orchestration6_DB.py
│   │   │   └── orchestration7.py
│   │   └── langchain/
│   │       ├── state.py
│   │       ├── cleaner.py
│   │       ├── classifier.py
│   │       ├── decider.py
│   │       └── workflow.py
│   └── db/
│       ├── supabase.py
│       ├── incidents.py
│       ├── feedback.py
│       └── mock_reports.py
├── data/
│   ├── category_keywords.json
│   ├── mock_posts.json
│   └── sample_posts.json
├── docs/
│   └── DOCUMENTATION.md
└── frontend/
    ├── package.json
    ├── next.config.ts
    └── src/
        ├── app/
        └── components/safewatch/
```

| Folder | What's in it |
|---|---|
| `backend/` | FastAPI server, all agents, and database helpers |
| `frontend/` | Next.js app — map, sidebar, incident detail panel |
| `data/` | Test posts and crawler output files |
| `docs/` | Full project documentation |

---

## Setup Instructions

### Prerequisites

- Python 3.10+
- Node.js 18+

### Backend

**1. Create and activate a virtual environment:**

```bash
cd HORNY_APPLE/backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# Mac/Linux
source .venv/bin/activate
```

**2. Install dependencies:**

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**3. Set up environment variables:**

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | Yes | Used by all LLM agents |
| `SUPABASE_URL` | Yes | Your Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | Service role key — bypasses row-level security |
| `SUPABASE_ANON_KEY` | Optional | Fallback if service role key is missing |
| `SUPABASE_KEY` | Yes (crawler) | Used by `reddit_crawler.py` |
| `REDDIT_USER_AGENT` | Optional | Custom User-Agent for Reddit requests |
| `HUGGINGFACEHUB_API_TOKEN` | Optional | Used by the Reddit crawler's classifier |

> **Vercel / frontend deployment:** Next.js only exposes variables to the browser if they start with `NEXT_PUBLIC_`. Add `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` in your Vercel project settings.

**4. Start the API server (from `HORNY_APPLE/`):**

```bash
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

**5. Run the full LangGraph pipeline manually:**

```bash
python -m backend.orchestration
```

### Frontend

```bash
cd HORNY_APPLE/frontend
npm install
npm run dev   # → http://localhost:3000
```

---

## How to Navigate the Project

| If you want to… | Look here |
|---|---|
| Change agent logic (crawling, cleaning, classifying, deciding) | `backend/agents/` |
| Change database queries or table operations | `backend/db/` |
| Change the map, sidebar, or incident panel | `frontend/src/components/safewatch/` |
| Change the LangGraph pipeline graph (nodes, edges, routing) | `backend/agents/langchain/workflow.py` |
| Add or edit crime categories and their keywords | `backend/agents/crawler/deterministic.py` (`CATEGORY_RULES`) and `data/category_keywords.json` |
| Add a new API route | `backend/main.py` |

The full technical reference for every file and function is in [`docs/DOCUMENTATION.md`](docs/DOCUMENTATION.md).

---

## API Reference (Summary)

| Method | Path | What it does |
|---|---|---|
| `GET` | `/` | API info and database connection status |
| `GET` | `/health` | Health check |
| `GET` | `/api/incidents` | Runs crawler on local JSON file (no database) |
| `GET` | `/api/db/incidents` | Gets incidents from Supabase |
| `GET` | `/api/db/incidents/{id}` | Gets one incident by UUID |
| `GET` | `/api/db/incidents/{id}/feedback` | Gets agent feedback history for one incident |
| `POST` | `/api/db/incidents` | Saves a new incident |
| `POST` | `/api/db/incidents/{id}/feedback` | Sends agent-to-agent feedback |
| `GET` | `/api/db/official-reports` | Gets all mock official reports |
| `POST` | `/api/pipeline/run` | Runs the LangGraph pipeline on a list of posts |

Interactive docs available at `http://127.0.0.1:8000/docs` when the server is running.

---

## Known Limitations

- **[High]** `langchain/classifier.py` — Vandalism (0.64) and harassment (0.66) scores are hardcoded below the 0.70 publish threshold. These two crime types can never be published through the main LangGraph pipeline path.
- **[High]** Standalone pipelines (`orchestration6_DB.py`, `orchestration7.py`) do not write decisions back to Supabase. Only the `POST /api/pipeline/run` path (via `langchain/decider.py`) saves results to the database.
- **[High]** The LangGraph graph in `langchain/workflow.py` has no automatic trigger. It must be called via `POST /api/pipeline/run` or run manually from the command line.
