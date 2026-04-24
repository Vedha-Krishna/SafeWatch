# Vercel Cron Setup

This project uses Vercel Cron as a scheduler, not as the Python worker itself.

Flow:

```txt
Vercel Cron
  -> GET /api/cron/safewatch in the Next.js app
  -> validates CRON_SECRET
  -> calls BACKEND_CRON_URL
  -> FastAPI validates CRON_SECRET
  -> runs crawler -> cleaner -> process_incidents/classifier/decider
```

## Files Added

| File | Purpose |
|---|---|
| `frontend/vercel.json` | Registers the cron schedule with Vercel. |
| `frontend/src/app/api/cron/safewatch/route.ts` | Vercel Function called every 10 minutes. |
| `backend/cron_pipeline.py` | Runs the backend cron pipeline in order. |
| `backend/main.py` | Exposes `GET /api/cron/safewatch` for the backend. |

## Schedule

The schedule is in `frontend/vercel.json`:

```json
{
  "crons": [
    {
      "path": "/api/cron/safewatch",
      "schedule": "*/10 * * * *"
    }
  ]
}
```

`*/10 * * * *` means every 10 minutes. Vercel cron schedules use UTC.

## Vercel Project Settings

If your Vercel project deploys the Next.js app, set the Vercel Root Directory to:

```txt
frontend
```

That lets Vercel read `frontend/vercel.json` and create the cron job.

If your Vercel Root Directory is the repository root instead, move the `vercel.json`
configuration to the actual Vercel project root.

## Environment Variables

Set these in the Vercel frontend project:

```txt
CRON_SECRET=use-a-random-secret-at-least-16-characters
BACKEND_CRON_URL=https://your-backend-domain.com/api/cron/safewatch
BACKEND_CRON_TIMEOUT_MS=55000
```

Set these in the backend host:

```txt
CRON_SECRET=same-value-as-vercel-frontend
OPENAI_API_KEY=...
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
REDDIT_USER_AGENT=...
```

Optional backend batch controls:

```txt
CRON_CRAWLER_LIMIT=25
CRON_MAX_CLEANER_RUNS=5
CRON_MAX_PROCESS_INCIDENTS=5
CRON_INCLUDE_COMMENTS=false
```

The frontend and backend both check `Authorization: Bearer <CRON_SECRET>`.
Vercel automatically sends this header when `CRON_SECRET` exists in the project.

## Local Test

Start the backend:

```bash
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Call the backend directly:

```bash
curl -H "Authorization: Bearer $CRON_SECRET" \
  http://127.0.0.1:8000/api/cron/safewatch
```

Start the frontend:

```bash
cd frontend
npm run dev
```

Call the Vercel-facing route:

```bash
curl -H "Authorization: Bearer $CRON_SECRET" \
  http://localhost:3000/api/cron/safewatch
```

## Deployment Notes

- Vercel creates cron jobs only for production deployments.
- Vercel cron paths are HTTP GET requests, so the endpoint must return a normal response and must not redirect.
- A 10-minute schedule requires a Vercel plan that supports more than daily cron execution.
- If the full crawler/LLM pipeline takes too long for your host, keep the batch sizes low or move the heavy work into a queue/worker.
