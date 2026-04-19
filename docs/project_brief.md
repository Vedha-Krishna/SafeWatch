# PettyCrimeSingapore Project Brief

## Problem Statement
This project is for Theme E: AI-native infrastructure for agent systems.

Most software infrastructure assumes humans are the primary operators. This project explores how AI agents can coordinate with other agents, tools, and environments directly instead of relying on human-centered workflows.

## Solution
PettyCrimeSingapore is a multi-agent system that detects potentially unreported petty-crime or suspicious-activity incidents from community sources such as Reddit, forums, or mock social posts.

The system converts noisy, unstructured posts into structured incident objects, scores them, checks whether they appear unreported, and decides whether they should become pins on a Singapore map.

## What Counts as an Incident
An incident is an unreported real-world event involving suspected petty crime or suspicious activity, with enough detail to be reviewed and tracked.

Included MVP categories:
- Theft
- Attempted theft
- Vandalism
- Suspicious activity
- Harassment

Excluded:
- General opinions
- Vague warnings
- Non-crime complaints
- Memes/jokes
- Duplicate reposts
- Incidents already in official/mainstream sources
- Incidents already pinned in the system

## Agents

### 1. Crawler Agent
Role: Ingestion and structuring.

Responsibilities:
- Read sample posts
- Detect possible incident candidates
- Extract key fields into incident draft JSON
- Output raw text, source metadata, location/time clues, and evidence snippets

### 2. Classifier Agent
Role: Evaluation and scoring.

Responsibilities:
- Category classification
- Authenticity scoring
- Severity scoring
- Duplicate detection
- Unreported check
- Output reviewed incident metadata

Category scoring uses hybrid category scoring:
- Rule-based scoring
- Vector similarity scoring against prototype examples

Authenticity scoring uses rubric-guided LLM scoring:
- Detail specificity
- Evidence quality
- Source reliability
- Consistency
- Corroboration
- Risk flags

### 3. Decision Agent
Role: Final operational decision.

Responsibilities:
- Receive reviewed incident from Classifier Agent
- Decide publish, merge, reject, hold, or needs_revision
- Update incident state
- Prepare final map/dashboard-ready incident record

## Workflow
Crawler Agent → Classifier Agent → Decision Agent → Map/Dashboard

Feedback loops:
- Classifier → Crawler: missing source/context/location/time
- Decision Agent → Classifier: unclear/conflicting scores or labels
- Decision Agent → Crawler: missing source-level evidence

Revision loop limit:
- Maximum 2 revision attempts

## Shared Incident Schema
All agents communicate through one shared incident object.

Important fields:
- incident_id
- source_platform
- source_url
- raw_text
- category
- severity
- authenticity_score
- location_text
- latitude
- longitude
- timestamp_text
- normalized_time
- candidate_scores
- matched_signals
- status
- duplicate_of
- agent_notes

## Tech Stack
- Frontend: React.js
- Map: Leaflet or Mapbox
- Backend: FastAPI
- Agents: LangGraph
- LLM: Hugging Face / OpenAI / IBM watsonx
- Database: Supabase / PostgreSQL
- Vector Store: Supabase pgvector
- Input: Reddit API later, mock dataset for MVP

## MVP Scope
Use mock data first. Do not implement real scraping yet.

MVP should include:
- 15–30 sample posts
- Crawler, Classifier, and Decision agents
- LangGraph workflow
- Mock official-reported check
- Feedback loop demo
- Final output saved to `data/final_incidents.json`

The MVP goal is:

Noisy community post → structured incident draft → scored incident → final decision → map pin.

## Ethics / Safety
The system must treat posts as unverified reports, not confirmed crimes.

Rules:
- Do not claim legal truth
- Use confidence scores
- Do not publish names, faces, usernames, phone numbers, or personal details
- Publish only generalized/safe summaries
- Hold, revise, or reject low-confidence reports instead of amplifying them
