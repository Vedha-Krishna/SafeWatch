# PettyCrimeSingapore

Crawler-first MVP for turning mock community posts into structured incident drafts.

## Run the deterministic crawler

The crawler uses only the Python standard library and makes no LLM or network calls.

```powershell
python agents\crawler_agent.py
```

Input: `data/sample_posts.json`

Output: `data/incident_drafts.json`
