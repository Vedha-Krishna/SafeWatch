# PettyCrimeSG — Full Project Documentation

> **Hackathon project** | Theme E: AI-native infrastructure for agent systems  
> **Stack:** Python · FastAPI · LangGraph · OpenAI · Supabase · Next.js · Leaflet

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Repository Structure](#2-repository-structure)
3. [Architecture Overview](#3-architecture-overview)
4. [Data Flow — End to End](#4-data-flow--end-to-end)
5. [Backend](#5-backend)
   - 5.1 [FastAPI Application](#51-fastapi-application-backendmainpy)
   - 5.2 [Crawler Agent](#52-crawler-agent)
   - 5.3 [Cleaner Agent](#53-cleaner-agent)
   - 5.4 [Classifier Agent](#54-classifier-agent)
   - 5.5 [Decision Agent](#55-decision-agent)
   - 5.6 [LangGraph Pipeline](#56-langgraph-pipeline)
   - 5.7 [Multimodal Verifier](#57-multimodal-verifier-utility)
6. [Database Layer](#6-database-layer)
   - 6.1 [Supabase Client](#61-supabase-client)
   - 6.2 [Incidents Table](#62-incidents-table)
   - 6.3 [Agent Feedback Table](#63-agent-feedback-table)
   - 6.4 [Mock Official Reports Table](#64-mock-official-reports-table)
7. [API Reference](#7-api-reference)
8. [Frontend](#8-frontend)
   - 8.1 [Application Shell](#81-application-shell)
   - 8.2 [Zustand Store](#82-zustand-store)
   - 8.3 [Map View](#83-map-view)
   - 8.4 [Incident Detail Panel](#84-incident-detail-panel)
   - 8.5 [Severity Sidebar](#85-severity-sidebar)
   - 8.6 [Mock Data](#86-mock-data)
9. [Shared Data Schemas](#9-shared-data-schemas)
10. [Feedback Loop System](#10-feedback-loop-system)
11. [Environment Variables](#11-environment-variables)
12. [Setup and Running](#12-setup-and-running)
13. [Known Limitations and Bugs](#13-known-limitations-and-bugs)
14. [Ethics and Safety Rules](#14-ethics-and-safety-rules)

---

## 1. Project Overview

PettyCrimeSG is a multi-agent OSINT (Open Source Intelligence) system that monitors community posts from platforms like Reddit and automatically identifies, evaluates, and maps potentially unreported petty-crime incidents in Singapore.

**The core problem it solves:** Community members frequently post about petty crimes (theft, harassment, vandalism) on social media, but these reports are unstructured, noisy, and often go unnoticed by authorities. PettyCrimeSG converts these noisy posts into structured, scored, map-ready incident records using a pipeline of AI agents.

**What the system does:**

1. Ingests raw text posts from Reddit or mock JSON files
2. Filters posts by relevance — rejecting jokes, vague warnings, duplicates, and opinions
3. Extracts structured fields: crime category, location, time, and action
4. Scores each post for authenticity and severity using an LLM rubric
5. Decides whether to publish, reject, or retry each incident
6. Stores published incidents in a Supabase database
7. Displays them as interactive map pins on a live Singapore map

**Incident categories covered:**

| Category | Description |
|---|---|
| `theft` | Stealing, snatch theft, pickpocketing |
| `attempted_theft` | Tried but failed to steal |
| `vandalism` | Graffiti, property damage |
| `suspicious_activity` | Loitering, prowling, suspicious behaviour |
| `harassment` | Threats, intimidation, following |

**Posts that are always rejected:**

- Jokes, memes, satire
- General opinions ("Singapore is getting worse")
- Vague warnings ("be careful everyone")
- Non-crime complaints (train delays, bad service)
- Incidents already in official/mainstream news
- Duplicate reposts of the same incident

---

## 2. Repository Structure

```
HORNY_APPLE/
├── .env.example                    # Environment variable template
├── .gitignore
├── README.md                       # Quick-start guide
├── graph.png                       # LangGraph pipeline visualisation
│
├── backend/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app — all HTTP routes
│   ├── orchestration.py            # Standalone pipeline runner (CLI)
│   ├── requirements.txt            # Python dependencies
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   │
│   │   ├── cleaner/
│   │   │   └── cleaner_agent.py    # LLM-based cleaner (standalone)
│   │   │
│   │   ├── crawler/
│   │   │   ├── __init__.py
│   │   │   ├── deterministic.py    # Keyword-based crawler (main crawler)
│   │   │   ├── multimodal.py       # OpenAI vision/audio evidence verifier
│   │   │   ├── reddit_crawler.py   # Live Reddit scraper
│   │   │   ├── orchestration6_DB.py  # Full LangGraph pipeline v6 (LLM + DB)
│   │   │   ├── orchestration7.py     # Full LangGraph pipeline v7 (improved embeddings)
│   │   │   ├── orchestration2.py     # Earlier prototype
│   │   │   ├── orchestration3 LLM.py
│   │   │   ├── orchestration4 LLM.py
│   │   │   ├── orchestration5 LLM.py
│   │   │   ├── orchestration6 DB.py  # Duplicate (space in name)
│   │   │   ├── process incidents.py  # Earlier prototype
│   │   │   └── process_incidents.py  # Earlier prototype
│   │   │
│   │   └── langchain/
│   │       ├── __init__.py
│   │       ├── state.py            # LangGraph TypedDict state
│   │       ├── cleaner.py          # LangGraph cleaner node
│   │       ├── classifier.py       # LangGraph classifier node
│   │       ├── decider.py          # LangGraph decision node
│   │       └── workflow.py         # LangGraph graph assembly
│   │
│   └── db/
│       ├── __init__.py             # Package exports
│       ├── supabase.py             # Supabase client setup
│       ├── incidents.py            # incidents table CRUD
│       ├── feedback.py             # agent_feedback table CRUD
│       └── mock_reports.py         # mock_official_reports table CRUD
│
├── data/
│   ├── .gitkeep
│   ├── category_keywords.json      # Keyword definitions (reference)
│   ├── incident_drafts.json        # Crawler output (auto-generated)
│   ├── mock_posts.json             # 10 mock posts for pipeline testing
│   └── sample_posts.json           # 15+ mock posts for API testing
│
├── docs/
│   ├── .gitkeep
│   ├── project_brief.md            # Original project brief
│   └── DOCUMENTATION.md            # This file
│
└── frontend/
    ├── .gitignore
    ├── eslint.config.mjs
    ├── next.config.ts
    ├── package.json
    ├── postcss.config.mjs
    ├── tsconfig.json
    │
    ├── public/
    │   ├── file.svg
    │   ├── globe.svg
    │   ├── next.svg
    │   ├── vercel.svg
    │   ├── window.svg
    │   └── data/
    │       └── sg-planning-areas.geojson   # Singapore planning area polygons
    │
    └── src/
        ├── App.tsx
        ├── index.css
        ├── app/
        │   ├── favicon.ico
        │   ├── globals.css
        │   ├── layout.tsx
        │   └── page.tsx
        └── components/
            └── safewatch/
                ├── Dashboard.tsx           # Root layout component
                ├── Header.tsx              # Top navigation bar
                ├── MapView.tsx             # Leaflet map with pins
                ├── IncidentDetailPanel.tsx # Slide-in incident detail
                ├── SeveritySidebar.tsx     # Filterable incident list
                ├── mockData.ts             # 55 mock incidents + types
                └── store.ts                # Zustand global state
```

---

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                             │
│  Reddit r/singapore (live)    Mock JSON files (development)     │
└──────────────────┬──────────────────────────────────────────────┘
                   │ raw text posts
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                      CRAWLER AGENT                              │
│  deterministic.py — keyword filtering, rejection rules,         │
│  duplicate detection, location/time extraction                  │
│                                                                 │
│  reddit_crawler.py — live Reddit scraper with HuggingFace       │
│  zero-shot classifier for relevance filtering                   │
└──────────────────┬──────────────────────────────────────────────┘
                   │ candidate incident drafts
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                      CLEANER AGENT                              │
│  cleaner_agent.py — GPT-4o-mini rewrites raw text into formal   │
│  1-2 sentence summary; normalises location, time, coordinates   │
└──────────────────┬──────────────────────────────────────────────┘
                   │ cleaned incident
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                     CLASSIFIER AGENT                            │
│  orchestration6_DB.py / orchestration7.py                       │
│  — Vector similarity category selection (OpenAI embeddings)     │
│  — LLM rubric-based authenticity scoring                        │
│  — LLM severity scoring                                         │
└──────────────────┬──────────────────────────────────────────────┘
                   │ scored incident
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DECISION AGENT                             │
│  — LLM final verdict: publish / needs_retry / reject            │
│  — Max 2 revision cycles                                        │
│  — Sends feedback messages to Classifier if needs_retry         │
└──────────────────┬──────────────────────────────────────────────┘
                   │ publish decision
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                     SUPABASE DATABASE                           │
│  incidents table — published, rejected, queued, in_progress     │
│  agent_feedback table — inter-agent feedback messages           │
│  mock_official_reports table — official report reference data   │
└──────────────────┬──────────────────────────────────────────────┘
                   │ GET /api/db/incidents?published_only=true
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND                              │
│  main.py — serves incidents, feedback, and official reports     │
└──────────────────┬──────────────────────────────────────────────┘
                   │ JSON over HTTP
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                   NEXT.JS FRONTEND                              │
│  Leaflet map — Singapore planning area pins, severity colours   │
│  Filters — crime type, time range                               │
│  Sidebar — incident list with severity indicators               │
│  Detail panel — full incident breakdown with agent analysis     │
└─────────────────────────────────────────────────────────────────┘
```

**Feedback loops** run in the opposite direction when an agent cannot complete its task:

```
Decision Agent → Classifier  (re-evaluate ambiguous scores)
Classifier     → Crawler     (location unclear, find more details)
```

---

## 4. Data Flow — End to End

### Step 1 — Post ingestion

A raw post enters the pipeline as a plain dictionary with these fields:

```json
{
  "post_id": "mock_001",
  "platform": "mock_forum",
  "source_url": "mock://community/mock_001",
  "timestamp": "2026-04-18T22:15:00+08:00",
  "text": "My bicycle was stolen outside Bedok MRT last night."
}
```

### Step 2 — Crawler processing (`deterministic.py`)

The deterministic crawler:
1. Sanitises text — strips `@mentions` and phone numbers
2. Runs rejection rules — rejects jokes, vague warnings, opinions
3. Runs keyword scoring — matches against 5 crime category keyword lists
4. Checks for duplicates — compares normalised text against seen posts
5. Extracts location — substring-matches against 28 Singapore place names
6. Extracts time — regex-matches against time phrases

Output: an **incident draft** with `candidate: true/false`, `status`, `category`, `location_text`, `timestamp_text`, `lat: null`, `lng: null`.

### Step 3 — Cleaner processing (`cleaner_agent.py`)

For queued incidents in Supabase with `status=queued` and no `cleaned_content`:
1. Locks the incident (`status=in_progress`, `locked_by=cleaner_agent`)
2. Sends `raw_text` to GPT-4o-mini with instructions to produce a `CleanedIncident` object
3. The LLM outputs: `cleaned_content`, `topic_bucket`, `location_text`, `latitude`, `longitude`, `normalized_time`
4. Writes results back to Supabase and resets `status=queued` for the classifier

### Step 4 — Classification (`orchestration6_DB.py` / `orchestration7.py`)

The LangGraph classifier node:
1. Sends `raw_text` to GPT-4o-mini to extract `location`, `time`, `action` as structured fields
2. Embeds the text using `text-embedding-3-small`
3. Computes cosine similarity against category prototype embeddings to select the best crime category
4. Sends `raw_text` + extracted fields to GPT-4o-mini with a 19-feature rubric prompt
5. Computes `authenticity_score` and `severity` from the rubric feature flags

### Step 5 — Decision (`decision_node` in orchestration files)

The Decision Agent:
1. Receives `category`, `authenticity_score`, `severity`, `location`, `time`, `action`, `retry_count`
2. Asks GPT to decide: `publish`, `needs_retry`, or `reject`
3. If `needs_retry` and `retry_count < 2`: increments retry count, sends feedback to Classifier, routes back
4. If `retry_count >= 2`: forces `reject`
5. If `publish` or `reject`: ends the graph

### Step 6 — Storage and display

Published incidents are stored in Supabase's `incidents` table with `status=published`. The FastAPI endpoint `GET /api/db/incidents?published_only=true` serves them to the frontend. The Next.js map reads `location.area` to match each incident to a Singapore planning area polygon and displays a heat-density pin.

---

## 5. Backend

### 5.1 FastAPI Application (`backend/main.py`)

The entry point for all HTTP traffic. Starts with:

```bash
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Interactive docs: `http://127.0.0.1:8000/docs`

**CORS:** Allows `localhost:3000` and `127.0.0.1:3000` (the Next.js dev server).

**Route summary:**

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | API info, database status |
| `GET` | `/health` | Health check |
| `GET` | `/api/incidents` | Incidents from local JSON file (dev fallback) |
| `GET` | `/api/db/incidents` | Incidents from Supabase |
| `GET` | `/api/db/incidents/{id}` | Single incident by UUID |
| `GET` | `/api/db/incidents/{id}/feedback` | Agent feedback log for incident |
| `POST` | `/api/db/incidents` | Save a new incident |
| `POST` | `/api/db/incidents/{id}/feedback` | Send agent feedback |
| `GET` | `/api/db/official-reports` | All mock official reports |

**Query parameters for `GET /api/db/incidents`:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `status` | `string` | `null` | Filter by status (`published`, `rejected`, etc.) |
| `published_only` | `bool` | `false` | Shortcut: return only published incidents |
| `limit` | `int` | `50` | Max rows returned (1–500) |

---

### 5.2 Crawler Agent

There are two crawler implementations:

#### `deterministic.py` — Keyword-based crawler

Used as the primary development crawler. Processes posts from `data/sample_posts.json`.

**Constants:**

| Constant | Purpose |
|---|---|
| `CATEGORY_RULES` | 5 crime categories, each with a list of trigger keywords |
| `REJECTION_RULES` | 5 rejection categories (joke, vague, opinion, complaint, mainstream) |
| `LOCATION_HINTS` | 28 Singapore place names for string matching |
| `TIME_PATTERNS` | 4 regex patterns for relative and absolute time expressions |

**Scoring formula:**

```
score = min(1.0, 0.35 + (0.25 × number_of_keyword_matches))
```

Scores cap at: 1 match → 0.60, 2 matches → 0.85. Latitude and longitude are always `None` — geocoding is delegated to the Cleaner Agent.

**Key functions:**

| Function | Description |
|---|---|
| `sanitize_text(text)` | Strips @mentions and phone numbers |
| `score_categories(text)` | Returns per-category keyword hit scores |
| `pick_category(scores)` | Selects the top category by score + priority tiebreaker |
| `extract_location(text)` | Returns the first matching Singapore place name |
| `extract_time(text)` | Returns the first regex-matched time phrase |
| `rejection_reason(text)` | Returns the first matched rejection rule label |
| `process_post(post, seen)` | Full pipeline for one post; returns incident draft dict |
| `process_posts(posts)` | Batch-processes a list of posts |
| `load_posts(path)` | Reads and validates a JSON posts file |

**Running the crawler standalone:**

```bash
python -m backend.agents.crawler.deterministic --input data/sample_posts.json --output data/incident_drafts.json
```

#### `reddit_crawler.py` — Live Reddit scraper

Fetches posts from `r/singapore` using Reddit's public JSON API (no OAuth required). Uses a HuggingFace zero-shot classifier (`facebook/bart-large-mnli`) to filter posts by relevance before saving them to Supabase.

**Key constants:**

| Constant | Value | Description |
|---|---|---|
| `DEFAULT_SUBREDDIT` | `"singapore"` | Target subreddit |
| `RELEVANT_LABEL` | `"petty crime, theft, or scam"` | Positive class for zero-shot |
| `OTHER_LABEL` | `"general news or casual conversation"` | Negative class |
| `RELEVANCE_THRESHOLD` | `0.25` | Minimum confidence to keep a post |
| `DEFAULT_REQUEST_DELAY` | `0.35s` | Polite delay between Reddit requests |
| `DEFAULT_MAX_RETRIES` | `5` | Retry attempts on 429/5xx errors |

**Deduplication:** Queries the most recent `source_item_id` already in Supabase and stops scraping when it encounters a known post ID (incremental mode). Uses `dedupe_key = "reddit_{post_id}"` with Supabase upsert to prevent duplicate rows.

**Comment enrichment:** If `--include-comments` is set, posts that fail the first relevance check are re-evaluated after fetching up to 10 comment bodies.

**Running the scraper:**

```bash
# Dry run — print matching posts as JSON
python -m backend.agents.crawler.reddit_crawler --stats --pretty

# Save to Supabase
python -m backend.agents.crawler.reddit_crawler --upload --stats

# Backfill 100 newest posts, ignoring checkpoint
python -m backend.agents.crawler.reddit_crawler --backfill --upload
```

---

### 5.3 Cleaner Agent

**File:** `backend/agents/cleaner/cleaner_agent.py`

A standalone LLM-based agent that runs on Supabase-stored incidents. Processes one incident per invocation.

**Pydantic output schema — `CleanedIncident`:**

| Field | Type | Description |
|---|---|---|
| `cleaned_content` | `str` | Formal 1–2 sentence summary, slang and handles removed |
| `topic_bucket` | `Literal` | `singapore_news`, `singapore_viral`, or `other` |
| `location_text` | `str?` | Normalised place name (e.g. "Ang Mo Kio MRT") |
| `latitude` | `float?` | Approximate latitude (Singapore bounds: 1.1–1.5) |
| `longitude` | `float?` | Approximate longitude (Singapore bounds: 103.6–104.1) |
| `normalized_time` | `str?` | ISO-8601 timestamp in SGT (e.g. `2026-04-23T20:00:00+08:00`) |

**LLM behaviour (GPT-4o-mini, `temperature=0`):**
- Rewrites noisy community text as a formal objective summary
- Converts relative time phrases ("ytd", "last night") to absolute ISO-8601 using the current SGT time injected at runtime
- Geocodes Singapore locations to approximate decimal coordinates
- Categorises the post as news, viral, or other

**Locking mechanism:** Before processing, the agent sets `status=in_progress` and `locked_by=cleaner_agent`. If a concurrent process already locked the record, it skips to the next candidate. On success: resets to `status=queued` for the next agent. On failure: sets `status=failed` with `last_error`.

**Running:**

```bash
python -m backend.agents.cleaner.cleaner_agent
```

---

### 5.4 Classifier Agent

The classifier is implemented twice — a simple version in the `langchain/` package and a full version in the orchestration files.

#### `langchain/classifier.py` — Simple (LangGraph pipeline only)

Hardcoded keyword-based scoring. Returns scores of 0.35, 0.64, 0.66, or 0.78. **Known bug:** vandalism (0.64) and harassment (0.66) scores fall below the Decision Agent's 0.70 publish threshold, meaning those categories can never be published through this pipeline path.

#### `orchestration6_DB.py` / `orchestration7.py` — Full classifier

**Step 1 — LLM field extraction:** Sends `raw_text` to GPT-4o-mini and asks for `location`, `time`, `action` (and `incident_summary` in v7) as structured JSON.

**Step 2 — Vector similarity category selection:**
- Embeds the text using `text-embedding-3-small`
- Computes cosine similarity against pre-computed category prototype embeddings
- Selects the category with the highest max similarity score
- v6 has 4 categories with single prototype each; v7 has 10 categories with 3–4 prototypes each

**Step 3 — Rubric-based authenticity scoring:** Sends `raw_text` + extracted fields to GPT-4o-mini with a 19-feature boolean rubric across 4 dimensions:

| Dimension | Weight | Features |
|---|---|---|
| Detail specificity | 25% | specific_location, specific_time, specific_action, object_or_person, consequence |
| Evidence quality | 25% | firsthand_report, clear_description, media_mentioned, source_link, follow_up_details |
| Consistency | 15% | no_contradictions, time_location_action_align, category_matches, no_exaggeration |
| Risk flags | −5% | rumor_language, missing_location, missing_time, ragebait, contradiction |

```
authenticity_score = (0.25 × detail) + (0.25 × evidence) + (0.15 × consistency) − (0.05 × risk)
```

**Step 4 — Severity:**

```
severity = (0.4 × detail) + (0.3 × evidence) + (0.3 × risk)
```

---

### 5.5 Decision Agent

Implemented as `decision_node` inside `orchestration6_DB.py` and `orchestration7.py`.

**Inputs from state:** `category`, `authenticity_score`, `severity`, `location`, `time`, `action`, `retry_count`

**Logic:**
1. If `retry_count >= 2`: force `reject` without calling LLM (hard guard)
2. Otherwise: send incident data to GPT with instructions to return one of `publish`, `needs_retry`, `reject`
3. If `needs_retry`: increment `retry_count`, append a feedback message to `state["messages"]` with `feedback_to: "classifier"`, route back to crawler node
4. If `publish` or `reject`: end the graph

**Decision thresholds (from the LLM prompt):**
- Scores ≥ 0.25 with concrete location + time + action can be published
- Community reports do not require police confirmation, media links, or corroboration
- `needs_retry` is only used when missing information could realistically be improved

**Note:** `orchestration7.py` contains a typo — model `"gpt-5-mini"` does not exist. This will throw a runtime error; it should be `"gpt-4o-mini"`.

---

### 5.6 LangGraph Pipeline

Two complete pipeline implementations exist side by side:

#### `langchain/workflow.py` — Simple pipeline (3 nodes)

```
START → crawler_node → cleaner_node → classifier_node → decision_node → END
                                                              ↑
                              (if needs_revision and retry_count < 2) ←──
```

Uses the simplified nodes from `langchain/`. Does not write to Supabase. For learning/demo purposes.

#### `orchestration6_DB.py` / `orchestration7.py` — Full pipeline

```
START → crawler_node → classifier_node → decision_node → END
                                              ↑
                     (if needs_retry and retry_count < 2) ←──
```

Note: there is no separate cleaner node in these files — the classifier node performs both extraction and scoring.

**State schema (both implementations):**

| Field | Type | Set by |
|---|---|---|
| `incident_id` | `int` | Input |
| `source_platform` | `str` | Crawler |
| `source_url` | `str` | Crawler |
| `raw_text` | `str` | Input |
| `location` | `str?` | Classifier |
| `time` | `str?` | Classifier |
| `action` | `str?` | Classifier |
| `incident_summary` | `str?` | Classifier (v7 only) |
| `category` | `str?` | Classifier |
| `authenticity_score` | `float?` | Classifier |
| `severity` | `float?` | Classifier |
| `decision` | `str?` | Decision |
| `messages` | `list[dict]` | All agents |
| `retry_count` | `int` | Decision |

**Running the standalone pipeline:**

```bash
# Runs the langchain/workflow.py pipeline on a hardcoded test post
python -m backend.orchestration

# Runs orchestration6_DB.py on data/mock_posts.json
python -m backend.agents.crawler.orchestration6_DB
```

---

### 5.7 Multimodal Verifier Utility

**File:** `backend/agents/crawler/multimodal.py`

A standalone utility (not connected to the main pipeline) that verifies whether attached media files support a given post text. Uses OpenAI's vision, transcription, and chat APIs.

**Supported file types:**

| Type | Extensions | Method |
|---|---|---|
| Images | `.png`, `.jpg`, `.jpeg`, `.webp` | GPT-4.1-mini vision |
| Documents | `.pdf`, `.docx`, `.txt`, `.md`, `.csv`, `.json` | Text extraction + GPT summarisation |
| Videos | `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm` | Frame sampling + ffmpeg audio transcription |
| Audio | `.mp3`, `.wav`, `.m4a`, `.ogg` | Whisper transcription + GPT summarisation |

**Main function:**

```python
result = verify_post_against_evidence(post_text, evidence_paths)
# Returns: { support, confidence, reasoning, matched_claims, missing_claims, contradictions }
```

**LangGraph node:** `multimodal_verifier_node(state)` — can be added to a graph. Skips silently if `state["evidence_paths"]` is empty.

---

## 6. Database Layer

All database logic lives in `backend/db/`. The package exports everything from `backend/db/__init__.py`.

### 6.1 Supabase Client

**File:** `backend/db/supabase.py`

Uses `@lru_cache(maxsize=1)` to create one shared client per process.

Credential resolution order:
1. `SUPABASE_SERVICE_ROLE_KEY` (preferred — bypasses Row Level Security)
2. `SUPABASE_ANON_KEY` (fallback — subject to RLS policies)

```python
from backend.db import is_supabase_configured, get_supabase_client

if is_supabase_configured():
    client = get_supabase_client()
```

---

### 6.2 Incidents Table

**File:** `backend/db/incidents.py`

**Table:** `incidents`

| Column | Type | Description |
|---|---|---|
| `incident_id` | `uuid` | Auto-generated primary key |
| `source_platform` | `text` | e.g. `"reddit"`, `"mock_forum"` |
| `source_type` | `text` | e.g. `"post"` |
| `source_item_id` | `text` | Platform-specific post ID |
| `source_url` | `text` | Link to original post |
| `raw_text` | `text` | Original unmodified post content |
| `cleaned_content` | `text` | LLM-cleaned formal summary |
| `topic_bucket` | `text` | `singapore_news`, `singapore_viral`, `other` |
| `category` | `text` | Crime type |
| `authenticity_score` | `float` | 0.0 (fake) → 1.0 (certain) |
| `severity` | `float` | 0.0 (minor) → 1.0 (severe) |
| `location_text` | `text` | Human-readable place name |
| `latitude` | `float` | GPS latitude (Singapore: ~1.1–1.5) |
| `longitude` | `float` | GPS longitude (Singapore: ~103.6–104.1) |
| `timestamp_text` | `text` | Raw time phrase from post |
| `normalized_time` | `timestamptz` | ISO-8601 in SGT |
| `candidate_scores` | `jsonb` | Per-category keyword scores |
| `matched_signals` | `jsonb` | Matched keyword signals |
| `status` | `text` | See status values below |
| `duplicate_of` | `uuid` | Foreign key to original if duplicate |
| `decision` | `text` | Final agent decision |
| `dedupe_key` | `text` | Unique platform deduplication key |
| `agent_notes` | `jsonb` | Array of agent reasoning strings |
| `locked_by` | `text` | Which agent locked this row |
| `locked_at` | `timestamptz` | When the lock was acquired |
| `last_error` | `text` | Error message if status=failed |
| `available_at` | `timestamptz` | Earliest time this can be processed |
| `created_at` | `timestamptz` | Auto-set by Supabase |
| `updated_at` | `timestamptz` | Auto-set by Supabase |

**Status values:**

| Status | Meaning |
|---|---|
| `raw` | Just ingested, not processed |
| `queued` | Ready for the next agent |
| `in_progress` | Currently locked by an agent |
| `candidate` | Crawler approved it |
| `classified` | Classifier scored it |
| `published` | Approved — visible on the map |
| `rejected` | Rejected — not shown |
| `rejected_duplicate` | Duplicate of an earlier post |
| `merged` | Combined into another incident |
| `needs_revision` | Sent back for more information |
| `needs_context` | Has a crime signal but no location or time |
| `failed` | Agent encountered an error |

**Available functions:**

```python
insert_incident(data: dict) -> dict
get_incident_by_id(incident_id: str) -> dict | None
get_all_incidents(status_filter=None, limit=50) -> list[dict]
get_published_incidents(limit=100) -> list[dict]
get_candidate_incidents(limit=100) -> list[dict]
update_incident(incident_id: str, updates: dict) -> dict
update_incident_status(incident_id: str, new_status: str) -> dict
append_agent_note(incident_id: str, note: str, existing_notes: list) -> dict
```

---

### 6.3 Agent Feedback Table

**File:** `backend/db/feedback.py`

**Table:** `agent_feedback`

| Column | Type | Description |
|---|---|---|
| `id` | `uuid` | Auto-generated primary key |
| `incident_id` | `uuid` | Which incident this feedback is about |
| `from_agent` | `text` | Sender: `"crawler"`, `"classifier"`, `"decision_agent"` |
| `to_agent` | `text` | Recipient: `"crawler"`, `"classifier"`, `"decision_agent"` |
| `feedback_type` | `text` | Short code: `location_unclear`, `time_missing`, etc. |
| `reason` | `text` | Human-readable explanation |
| `requested_action` | `text` | Specific instruction for the recipient |
| `priority` | `text` | `"low"`, `"medium"`, `"high"` |
| `resolved` | `boolean` | Has this been acted on? Default `false` |
| `created_at` | `timestamptz` | Auto-set by Supabase |

**Feedback type codes:**

`location_unclear`, `time_missing`, `source_weak`, `text_too_vague`, `possible_duplicate`, `authenticity_too_low`, `category_conflict`, `severity_unclear`, `source_metadata_missing`

**Available functions:**

```python
insert_feedback(data: dict) -> dict
get_feedback_for_incident(incident_id: str) -> list[dict]
get_unresolved_feedback(to_agent: str | None = None) -> list[dict]
get_all_feedback(limit=100) -> list[dict]
mark_feedback_resolved(feedback_id: str) -> dict
resolve_all_feedback_for_incident(incident_id: str) -> list[dict]
```

---

### 6.4 Mock Official Reports Table

**File:** `backend/db/mock_reports.py`

**Table:** `mock_official_reports`

Stands in for real Singapore Police Force, CNA, and Straits Times records. Used by the Classifier Agent to check whether a community post duplicates an already-officially-reported incident.

| Column | Type | Description |
|---|---|---|
| `id` | `uuid` | Auto-generated primary key |
| `title` | `text` | Short headline |
| `description` | `text` | Full description |
| `category` | `text` | Crime type |
| `location_text` | `text` | Human-readable location |
| `latitude` | `float` | GPS latitude |
| `longitude` | `float` | GPS longitude |
| `reported_at` | `timestamptz` | When officially reported |
| `source` | `text` | `"SPF"`, `"CNA"`, `"Straits Times"` |

**Available functions:**

```python
get_all_mock_reports() -> list[dict]
find_similar_official_report(category: str, location_text: str) -> dict | None
get_reports_by_category(category: str) -> list[dict]
insert_mock_report(data: dict) -> dict
seed_mock_reports(reports: list[dict]) -> list[dict]
```

`find_similar_official_report` matches on exact `category` + case-insensitive partial `location_text`. Known limitation: will miss the same location described with different wording (e.g. "Bedok" vs "East Coast").

---

## 7. API Reference

Base URL (development): `http://127.0.0.1:8000`

---

### `GET /`

Returns API version info and database connection status.

**Response:**
```json
{
  "message": "PettyCrimeSG API is running.",
  "docs": "/docs",
  "database_connected": "True"
}
```

---

### `GET /health`

Health check.

**Response:**
```json
{ "status": "ok", "database": "connected" }
```

---

### `GET /api/incidents`

Processes `data/sample_posts.json` through the deterministic crawler in memory and returns the results. Does not use the database.

**Query params:** `candidate_only=true`, `limit=50`

**Response:**
```json
{
  "count": 12,
  "source": "json_file",
  "incidents": [...]
}
```

---

### `GET /api/db/incidents`

Reads incidents from Supabase. Primary endpoint for the frontend map.

**Query params:** `status=published`, `published_only=true`, `limit=50`

**Response:**
```json
{
  "count": 8,
  "source": "supabase",
  "incidents": [...]
}
```

---

### `GET /api/db/incidents/{incident_id}`

Returns a single incident by its UUID.

**404** if not found.

---

### `GET /api/db/incidents/{incident_id}/feedback`

Returns the complete agent conversation log for an incident.

**Response:**
```json
{
  "incident_id": "...",
  "count": 3,
  "feedback": [
    {
      "from_agent": "classifier",
      "to_agent": "crawler",
      "feedback_type": "location_unclear",
      "reason": "...",
      "requested_action": "...",
      "priority": "medium",
      "resolved": false
    }
  ]
}
```

---

### `POST /api/db/incidents`

Saves a new incident. Called by the Crawler Agent.

**Required body fields:** `source_platform`, `raw_text`, `status`

**Response:**
```json
{ "message": "Incident saved successfully.", "incident": {...} }
```

---

### `POST /api/db/incidents/{incident_id}/feedback`

Sends an agent-to-agent feedback message.

**Required body fields:** `from_agent`, `to_agent`, `feedback_type`, `reason`, `requested_action`, `priority`

---

### `GET /api/db/official-reports`

Returns all mock official reports. **Query param:** `limit=100`

---

## 8. Frontend

**Tech stack:** Next.js 16 (App Router), TypeScript, Tailwind CSS v4, React-Leaflet, Zustand, Framer Motion

**Start:**
```bash
cd frontend
npm install
npm run dev   # → http://localhost:3000
```

---

### 8.1 Application Shell

**`app/page.tsx`** → renders `<Dashboard />`  
**`app/layout.tsx`** → sets metadata, applies global CSS  
**`app/globals.css`** → Tailwind base styles + custom `safewatch-*` CSS classes for glass panels, pin animations, and map overlays

---

### 8.2 Zustand Store

**File:** `src/components/safewatch/store.ts`

Single source of truth for all UI state. Key slices:

| State field | Type | Description |
|---|---|---|
| `incidents` | `Incident[]` | Current incident list (starts with mock data) |
| `clusters` | `Cluster[]` | Cluster metadata |
| `selectedIncidentId` | `string?` | ID of the open detail panel |
| `crimeType` | `CrimeTypeFilter` | Active crime type filter |
| `timeRange` | `TimeRangeFilter` | Active time window (`24h`, `7d`, `30d`, `90d`) |
| `severityFilter` | `SeverityFilter` | Severity display mode |
| `mapFlyTo` | `object?` | Coordinates to animate the map to |
| `sidebarCollapsed` | `bool` | Sidebar open/closed |
| `isLoading` | `bool` | API fetch in progress |

**`fetchIncidents()`:** Calls `GET /api/db/incidents?published_only=true&limit=200`. If the API returns data, replaces mock incidents with real database rows (mapped via `mapDbIncidentToFrontend`). Falls back to mock data silently if the API is unreachable or returns zero rows.

**Database → frontend field mapping:**

| DB column | Frontend field | Notes |
|---|---|---|
| `incident_id` | `id` | |
| `authenticity_score` | `confidence` | |
| `authenticity_score ≥ 0.8` | `verified` | |
| `raw_text` | `description` | |
| `location_text` | `location.area` | |
| `latitude` | `location.lat` | Defaults to `1.3521` |
| `longitude` | `location.lng` | Defaults to `103.8198` |
| `normalized_time` | `timestamp` | |
| `severity float` | `severity string` | `≥0.9` → critical, `≥0.7` → high, `≥0.5` → medium, else → low |

**Selector hooks:**

```typescript
useFilteredIncidents()  // applies crimeType + timeRange filters
severityCounts(incidents)  // returns { critical, high, medium, low } counts
timeAgo(isoString)  // returns "5 min ago", "2 hrs ago", "3 days ago"
```

---

### 8.3 Map View

**File:** `src/components/safewatch/MapView.tsx`

Built on React-Leaflet. Locked to Singapore's bounding box (`[1.16, 103.6]` → `[1.48, 104.1]`). Zoom range: 12–18.

**Area aggregation:** Incidents are grouped by Singapore planning area. Each area gets one heat-density pin instead of individual markers. GeoJSON data for all planning areas is loaded lazily from `/data/sg-planning-areas.geojson`.

**Pin heat levels:**

| Count | Colour | Hex |
|---|---|---|
| 1 | Cyan | `#06b6d4` |
| 2–3 | Yellow | `#eab308` |
| 4–6 | Orange | `#f97316` |
| 7–9 | Red-orange | `#ef4444` |
| 10+ | Deep red | `#b91c1c` |

**Interaction:**
- Hover a pin → tooltip shows up to 5 incidents in that area
- Click a pin → popup shows the full area incident list; clicking an incident opens the detail panel and flies the map to that area
- Incidents that don't match any planning area get a fallback pushpin at their raw `lat/lng`

**Map styles** (switchable in-app):
- Voyager (default light)
- Dark Matter
- Positron
- Satellite (ArcGIS)

---

### 8.4 Incident Detail Panel

**File:** `src/components/safewatch/IncidentDetailPanel.tsx`

Slides in from the right when an incident is selected. Displays:
- Title, severity badge, verified status
- Location, timestamp, source
- Full description
- Agent analysis: classification confidence, validation status, severity reason, pattern notes

---

### 8.5 Severity Sidebar

**File:** `src/components/safewatch/SeveritySidebar.tsx`

Collapsible panel (collapsed on mobile by default). Contains:
- Crime type filter buttons
- Time range filter buttons
- Severity count summary
- Scrollable incident list with severity colour indicators

---

### 8.6 Mock Data

**File:** `src/components/safewatch/mockData.ts`

55 hardcoded incidents across 15+ Singapore planning areas. Used as the initial state when the store loads, and as fallback if the backend is unreachable. Includes 3 hardcoded clusters:

| Cluster | Type | Area | Incidents |
|---|---|---|---|
| `CL_023` | Snatch Theft | Geylang | 5 |
| `CL_019` | Bike Theft | Tampines MRT | 4 |
| `CL_031` | Voyeurism | Yishun Block 743 | 3 |

**Severity colour constants:**
```
critical → #ef4444 (red)
high     → #f97316 (orange)
medium   → #eab308 (yellow)
low      → #22c55e (green)
```

---

## 9. Shared Data Schemas

### Frontend `Incident` type

```typescript
interface Incident {
  id: string;
  type: string;                    // crime category
  severity: "critical" | "high" | "medium" | "low";
  title: string;
  description: string;
  location: { area: string; lat: number; lng: number };
  source: string;
  verified: boolean;               // confidence >= 0.8
  confidence: number;              // 0.0–1.0
  timestamp: string;               // ISO-8601
  cluster_id: string | null;
  agent_analysis: {
    classification: string;
    classification_confidence: number;
    validation: string;
    severity_reason: string;
    pattern: string;
  };
}
```

### Backend `CleanedIncident` (Pydantic)

```python
class CleanedIncident(BaseModel):
    cleaned_content: str
    topic_bucket: Literal["singapore_news", "singapore_viral", "other"]
    location_text: Optional[str]
    latitude: Optional[float]   # 1.1–1.5
    longitude: Optional[float]  # 103.6–104.1
    normalized_time: Optional[str]  # ISO-8601 SGT
```

### LangGraph `IncidentState` (TypedDict)

```python
class IncidentState(TypedDict):
    post_id: str
    raw_text: str
    candidate: Optional[bool]
    category: Optional[str]
    authenticity_score: Optional[float]
    decision: Optional[str]
    revision_count: int
    notes: list[str]
```

---

## 10. Feedback Loop System

The system supports three agent-to-agent feedback channels:

```
Classifier → Crawler      (e.g. "location unclear, find more details")
Decision   → Classifier   (e.g. "re-evaluate ambiguous category scores")
Decision   → Crawler      (e.g. "source metadata missing")
```

**In the orchestration pipelines** (`orchestration6_DB.py`, `orchestration7.py`): feedback messages are stored in `state["messages"]` as in-memory dicts with a `feedback_to` field. The receiving agent reads them at the start of its node.

**In Supabase** (`db/feedback.py`): feedback is persisted to the `agent_feedback` table. Agents can poll `get_unresolved_feedback(to_agent="crawler")` to check their inbox and call `mark_feedback_resolved(feedback_id)` when done.

**Via API** (`POST /api/db/incidents/{id}/feedback`): any component can send feedback to any agent through the REST API.

**Revision limit:** Maximum 2 retry cycles per incident. After 2 retries the decision node forces `reject` without calling the LLM.

---

## 11. Environment Variables

Copy `.env.example` to `.env` and fill in your values.

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | Yes | OpenAI API key (used by all LLM agents) |
| `SUPABASE_URL` | Yes (for DB) | Your Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes (for DB) | Service role key (backend only) |
| `SUPABASE_ANON_KEY` | Optional | Anon key (fallback if service role missing) |
| `SUPABASE_KEY` | Yes (for crawler) | Used specifically by `reddit_crawler.py` |
| `REDDIT_USER_AGENT` | Optional | Custom User-Agent for Reddit requests |

Without `SUPABASE_URL` and a key, the backend falls back to reading from `data/sample_posts.json` and the map shows mock data.

---

## 12. Setup and Running

### Backend

```bash
cd HORNY_APPLE/backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# Mac/Linux
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

Start the API server (run from `HORNY_APPLE/`):

```bash
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

```bash
cd HORNY_APPLE/frontend
npm install
npm run dev   # → http://localhost:3000
```

### Run agents manually

```bash
# Deterministic crawler — writes to data/incident_drafts.json
python -m backend.agents.crawler.deterministic

# Reddit crawler — scrape + save to Supabase
python -m backend.agents.crawler.reddit_crawler --upload --stats

# Cleaner agent — process one queued Supabase incident
python -m backend.agents.cleaner.cleaner_agent

# Simple LangGraph pipeline — one hardcoded test post
python -m backend.orchestration

# Full LangGraph pipeline — runs on data/mock_posts.json
python -m backend.agents.crawler.orchestration6_DB
```

### Database setup

Before running with a real database:

1. Create a Supabase project
2. Run `upgrade_migration.sql` in the Supabase SQL editor to create all tables
3. Run `seed_incidents.sql` to populate test data
4. Set `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in `.env`

---

## 13. Known Limitations and Bugs

| # | Severity | Location | Description |
|---|---|---|---|
| 1 | **Critical** | `langchain/classifier.py:17-18` | Vandalism (0.64) and harassment (0.66) scores are hardcoded below the 0.70 publish threshold in `decider.py`. These categories can never be published through the LangGraph pipeline path. |
| 2 | **Critical** | `orchestration7.py:570` | Decision node calls `model="gpt-5-mini"` which does not exist. Will throw a runtime API error. Should be `"gpt-4o-mini"`. |
| 3 | **High** | All orchestration pipelines | Pipeline does not write decisions back to Supabase. Published incidents never appear on the live map unless saved separately. |
| 4 | **High** | `langchain/workflow.py` | Not wired to FastAPI. There is no API endpoint to trigger the LangGraph pipeline. It can only be run as a standalone script. |
| 5 | **High** | `deterministic.py:308-309` | Crawler always sets `latitude: None`, `longitude: None`. Geocoding only happens if the Cleaner Agent runs separately afterwards. |
| 6 | **Medium** | `langchain/cleaner.py` | The LangGraph pipeline's cleaner node only does whitespace normalization. It does not set `location_text` or `normalized_time` on `IncidentState`, and those fields don't exist in the TypedDict. |
| 7 | **Medium** | `orchestration6_DB.py` | Classifier LLM calls do not set `temperature=0`, so results are non-deterministic across runs. |
| 8 | **Low** | `frontend/store.ts` | The map always starts with mock data on first load, even when the backend is available. `fetchIncidents()` is called on mount but there is a brief flash of mock data. |
| 9 | **Low** | `db/mock_reports.py` | `find_similar_official_report` uses simple string matching and will miss semantically equivalent locations described with different wording. |

---

## 14. Ethics and Safety Rules

All agents follow these rules, enforced via LLM system prompts:

1. **Posts are unverified reports, not confirmed crimes.** The system never asserts guilt or confirms a crime occurred.
2. **Confidence scores are always shown.** No incident is displayed without its `authenticity_score`.
3. **No personal information is published.** Names, faces, usernames, phone numbers, and personal details are stripped by the Cleaner Agent.
4. **Only generalised summaries are published.** The `cleaned_content` field is the only text shown publicly — the raw post text is stored but not displayed.
5. **Low-confidence reports are held or rejected.** Incidents below the authenticity threshold go to `needs_revision` or `rejected`, not directly to the map.
6. **Maximum 2 revision cycles.** After 2 retries, an uncertain incident is rejected rather than amplified.
7. **The map shows patterns, not accusations.** Pins represent community reports, not police records.
