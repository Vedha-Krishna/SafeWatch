from __future__ import annotations

"""
main.py - FastAPI application entry point for PettyCrimeSG.

This file defines all the HTTP API routes that the frontend React app calls.
FastAPI automatically generates interactive documentation at /docs when the
server is running.

HOW TO START THE SERVER:
    From the project root:
        python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000

    From inside the backend/ folder:
        python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000

    Then open http://127.0.0.1:8000/docs to see all routes with descriptions.

API ROUTE OVERVIEW:
    GET /                               - API info and link to docs
    GET /health                         - Health check (also shows DB status)
    GET /api/incidents                  - List incidents from JSON file (original endpoint)
    GET /api/cron/safewatch             - Trigger the scheduled pipeline (cron)
    GET /api/db/incidents               - List incidents from Supabase database
    GET /api/db/incidents/{id}          - Get a single incident by ID
    GET /api/db/incidents/{id}/feedback - Get all agent feedback for an incident
    GET /api/db/official-reports        - List all mock official reports
    POST /api/db/incidents              - Save a new incident to the database
    POST /api/db/incidents/{id}/feedback - Send agent-to-agent feedback for an incident
"""

import logging
import os
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# Import the crawler functions (used by the original JSON-based endpoint).
# The try/except handles two different ways to run the server:
#   - As a package: python -m uvicorn backend.main:app  ->  uses "from .agents..."
#   - From inside backend/: python -m uvicorn main:app  ->  uses "from agents..."
# -----------------------------------------------------------------------
try:
    from .agents.crawler.deterministic import load_posts, process_posts
    from .agents.langchain.workflow import graph as pipeline_graph
    from .cron_pipeline import run_safewatch_pipeline
    from .db import (
        is_supabase_configured,
        get_all_incidents,
        get_published_incidents,
        get_incident_by_id,
        insert_incident,
        get_feedback_for_incident,
        insert_feedback,
        get_all_mock_reports,
    )
except ImportError:
    from agents.crawler.deterministic import load_posts, process_posts
    from agents.langchain.workflow import graph as pipeline_graph
    from cron_pipeline import run_safewatch_pipeline
    from db import (
        is_supabase_configured,
        get_all_incidents,
        get_published_incidents,
        get_incident_by_id,
        insert_incident,
        get_feedback_for_incident,
        insert_feedback,
        get_all_mock_reports,
    )

# Path to the sample posts JSON file (used by the original endpoint)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = PROJECT_ROOT / "data" / "sample_posts.json"


# -----------------------------------------------------------------------
# Create the FastAPI application instance.
# The title and description appear in the auto-generated /docs page.
# -----------------------------------------------------------------------
app = FastAPI(
    title="PettyCrimeSG API",
    description=(
        "API for the PettyCrimeSG multi-agent incident tracking system. "
        "Agents ingest community posts, classify incidents, and publish them "
        "to a live map of Singapore."
    ),
    version="0.1.0",
)


# -----------------------------------------------------------------------
# CORS (Cross-Origin Resource Sharing) middleware.
# This allows the React frontend running on localhost:3000 to make HTTP
# requests to this backend running on localhost:8000. Without this,
# the browser would block the requests for security reasons.
# -----------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],     # Allow GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],     # Allow any request headers
)


# -----------------------------------------------------------------------
# HELPER FUNCTION - Used by the original JSON-based endpoint.
# -----------------------------------------------------------------------

def read_incident_drafts_from_json(input_path: Path = DEFAULT_INPUT_PATH) -> list[dict]:
    """
    Read and process community posts from a local JSON file.

    This is the original data source used before the Supabase database was
    connected. It is kept as a fallback for local development without a database.

    Args:
        input_path: Path to the sample_posts.json file.

    Returns:
        list[dict]: Processed incident draft objects.

    Raises:
        HTTPException 404: If the JSON file does not exist.
        HTTPException 400: If the JSON file is malformed.
    """
    if not input_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Input file not found: {input_path}. "
                   f"Make sure data/sample_posts.json exists.",
        )

    try:
        posts = load_posts(input_path)
        return process_posts(posts)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# -----------------------------------------------------------------------
# HELPER - Cron authorization
# -----------------------------------------------------------------------

def verify_cron_authorization(authorization: str | None) -> None:
    cron_secret = os.getenv("CRON_SECRET")
    if not cron_secret:
        raise HTTPException(status_code=500, detail="CRON_SECRET is not configured.")

    if authorization != f"Bearer {cron_secret}":
        raise HTTPException(status_code=401, detail="Unauthorized")


# -----------------------------------------------------------------------
# ROUTE: GET /
# -----------------------------------------------------------------------

@app.get("/")
def root() -> dict[str, str]:
    """
    API root - returns a welcome message and link to the docs.

    This is the first thing you see when you open the API URL in a browser.
    """
    return {
        "message": "PettyCrimeSG API is running.",
        "docs": "/docs",
        "database_connected": str(is_supabase_configured()),
    }


# -----------------------------------------------------------------------
# ROUTE: GET /health
# -----------------------------------------------------------------------

@app.get("/health")
def health() -> dict[str, str]:
    """
    Health check endpoint.

    Used by monitoring tools, Docker health checks, or just to verify the
    server is up. Also reports whether the Supabase database is configured.
    """
    return {
        "status": "ok",
        "database": "connected" if is_supabase_configured() else "not configured",
    }


# -----------------------------------------------------------------------
# ROUTE: GET /api/incidents
# (Original endpoint - reads from local JSON file, not the database)
# -----------------------------------------------------------------------

@app.get("/api/incidents")
def list_incidents_from_json(
    candidate_only: bool = Query(
        default=False,
        description="If true, return only incidents flagged as candidates by the crawler."
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of incidents to return (1-500)."
    ),
) -> dict[str, object]:
    """
    List incident drafts processed from the local sample_posts.json file.

    This is the ORIGINAL endpoint. It runs the crawler agent in memory against
    the local JSON data file and returns the results. It does NOT use the database.

    Use this endpoint for quick local testing without needing a database connection.
    For real data from Supabase, use GET /api/db/incidents instead.
    """
    # Process posts through the crawler pipeline
    incidents = read_incident_drafts_from_json()

    # Optionally filter to only show candidate incidents
    if candidate_only:
        incidents = [
            incident
            for incident in incidents
            if incident.get("candidate") is True
        ]

    # Apply the row limit
    incidents = incidents[:limit]

    return {
        "count": len(incidents),
        "source": "json_file",
        "incidents": incidents,
    }


# -----------------------------------------------------------------------
# ROUTE: GET /api/cron/safewatch
# -----------------------------------------------------------------------

@app.get("/api/cron/safewatch")
def run_safewatch_cron(
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    verify_cron_authorization(authorization)

    try:
        return run_safewatch_pipeline()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Cron pipeline failed: {exc}") from exc


# -----------------------------------------------------------------------
# ROUTES: /api/db/incidents - Database-backed incident endpoints
# -----------------------------------------------------------------------

@app.get("/api/db/incidents")
def list_incidents_from_database(
    status: str | None = Query(
        default=None,
        description=(
            "Filter by status. Options: raw, candidate, classified, "
            "processed, rejected, merged, needs_revision. "
            "Leave empty to get all statuses."
        )
    ),
    published_only: bool = Query(
        default=False,
        description="Shortcut: if true, return only published incidents (for the map)."
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of incidents to return (1-500)."
    ),
) -> dict[str, object]:
    """
    List incidents stored in the Supabase database.

    This is the PRIMARY endpoint for the frontend map and dashboard.
    Unlike /api/incidents, this reads from the actual database rather than
    a local JSON file, so it reflects the true current state of all incidents.

    Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to be set in .env.
    """
    # Check that the database credentials are configured before attempting a query
    if not is_supabase_configured():
        raise HTTPException(
            status_code=503,
            detail=(
                "Supabase database is not configured. "
                "Add SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to your .env file. "
                "See .env.example for the required format."
            ),
        )

    # Use the published_only shortcut if requested, otherwise apply the status filter
    if published_only:
        incidents = get_published_incidents(limit=limit)
    else:
        incidents = get_all_incidents(status_filter=status, limit=limit)

    return {
        "count": len(incidents),
        "source": "supabase",
        "incidents": incidents,
    }


@app.get("/api/db/incidents/{incident_id}")
def get_single_incident(incident_id: str) -> dict[str, object]:
    """
    Retrieve a single incident by its UUID.

    Use this when the frontend needs to show full details for a specific incident
    (e.g. when a user clicks on a map pin).

    Args:
        incident_id: The UUID of the incident to retrieve. This comes from the
                     incident_id column in the database.
    """
    if not is_supabase_configured():
        raise HTTPException(
            status_code=503,
            detail="Supabase database is not configured. See .env.example.",
        )

    # Look up the incident in the database
    incident = get_incident_by_id(incident_id)

    # If no incident was found with that ID, return a 404 error
    if incident is None:
        raise HTTPException(
            status_code=404,
            detail=f"No incident found with ID: {incident_id}",
        )

    return incident


@app.get("/api/db/incidents/{incident_id}/feedback")
def get_incident_feedback(incident_id: str) -> dict[str, object]:
    """
    Get the full agent feedback history for a specific incident.

    This shows the complete conversation between agents as they processed
    this incident - useful for understanding why an incident went through
    multiple revisions, or for displaying the agent reasoning in the dashboard.

    Args:
        incident_id: The UUID of the incident to get feedback for.
    """
    if not is_supabase_configured():
        raise HTTPException(
            status_code=503,
            detail="Supabase database is not configured. See .env.example.",
        )

    feedback_messages = get_feedback_for_incident(incident_id)

    return {
        "incident_id": incident_id,
        "count": len(feedback_messages),
        "feedback": feedback_messages,
    }


@app.post("/api/db/incidents")
def create_incident(incident_data: dict) -> dict[str, object]:
    """
    Save a new incident to the database.

    This endpoint is called by the Crawler Agent after it processes a community
    post and determines it may be a real incident worth investigating.

    The request body should be a JSON object matching the incidents table schema.
    At minimum, include: source_platform, source_url, raw_text, status.

    Returns the saved incident record, including the auto-generated incident_id.
    """
    if not is_supabase_configured():
        raise HTTPException(
            status_code=503,
            detail="Supabase database is not configured. See .env.example.",
        )

    # Validate that the minimum required fields are present
    required_fields = ["source_platform", "raw_text", "status"]
    missing_fields = [field for field in required_fields if field not in incident_data]

    if missing_fields:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Missing required fields: {', '.join(missing_fields)}. "
                f"Required fields are: {', '.join(required_fields)}"
            ),
        )

    # Save to the database and return the created record
    saved_incident = insert_incident(incident_data)

    return {
        "message": "Incident saved successfully.",
        "incident": saved_incident,
    }


@app.post("/api/db/incidents/{incident_id}/feedback")
def send_agent_feedback(incident_id: str, feedback_data: dict) -> dict[str, object]:
    """
    Send a feedback message from one agent to another for a specific incident.

    This is called as part of the agent-to-agent feedback loop (Section 8 of the
    project spec). For example, the Classifier Agent sends feedback to the Crawler
    when the incident location is unclear.

    Args:
        incident_id: The UUID of the incident this feedback is about.

    Request body should include:
        from_agent (str)       - e.g. "classifier"
        to_agent (str)         - e.g. "crawler"
        feedback_type (str)    - e.g. "location_unclear"
        reason (str)           - Why is this feedback being sent?
        requested_action (str) - What should the receiving agent do?
        priority (str)         - "low", "medium", or "high"
    """
    if not is_supabase_configured():
        raise HTTPException(
            status_code=503,
            detail="Supabase database is not configured. See .env.example.",
        )

    # Add the incident_id to the feedback data (it comes from the URL, not the body)
    feedback_data["incident_id"] = incident_id

    # Validate the required fields are present
    required_fields = ["from_agent", "to_agent", "feedback_type", "reason", "requested_action", "priority"]
    missing_fields = [field for field in required_fields if field not in feedback_data]

    if missing_fields:
        raise HTTPException(
            status_code=422,
            detail=f"Missing required fields: {', '.join(missing_fields)}.",
        )

    # Save the feedback to the database
    saved_feedback = insert_feedback(feedback_data)

    return {
        "message": "Feedback sent successfully.",
        "feedback": saved_feedback,
    }


# -----------------------------------------------------------------------
# ROUTE: GET /api/db/official-reports
# -----------------------------------------------------------------------

# -----------------------------------------------------------------------
# ROUTE: POST /api/pipeline/run
# -----------------------------------------------------------------------

class _PipelinePost(BaseModel):
    post_id: str
    raw_text: str


class _PipelineRunRequest(BaseModel):
    posts: list[_PipelinePost]


_DECISION_TO_STATUS = {
    "publish": "processed",
    "reject": "rejected",
    "needs_revision": "needs_revision",
}


@app.post("/api/pipeline/run")
def run_pipeline(request: _PipelineRunRequest) -> dict[str, object]:
    """
    Run the LangGraph pipeline on one or more raw posts.

    Each post is passed through the crawler -> cleaner -> classifier -> decider
    graph sequentially. The decider node writes the result to Supabase when
    the database is configured.

    Request body:
        { "posts": [{ "post_id": "...", "raw_text": "..." }] }

    Response:
        { "results": [{ "post_id", "decision", "category",
                         "authenticity_score", "status" }] }
    """
    results = []

    for post in request.posts:
        initial_state = {
            "post_id": post.post_id,
            "raw_text": post.raw_text,
            "candidate": None,
            "category": None,
            "authenticity_score": None,
            "decision": None,
            "revision_count": 0,
            "notes": [],
        }

        try:
            final_state = pipeline_graph.invoke(initial_state)
            decision = final_state.get("decision")
            results.append({
                "post_id": post.post_id,
                "decision": decision,
                "category": final_state.get("category"),
                "authenticity_score": final_state.get("authenticity_score"),
                "status": _DECISION_TO_STATUS.get(decision, decision),
            })
        except Exception as exc:
            logger.error("Pipeline failed for post %s: %s", post.post_id, exc)
            results.append({
                "post_id": post.post_id,
                "error": str(exc),
            })

    return {"results": results}


@app.get("/api/db/official-reports")
def list_official_reports(
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of official reports to return."
    ),
) -> dict[str, object]:
    """
    List all mock official reports from the database.

    These are the pre-populated records that stand in for real official crime
    reports from sources like SPF, CNA, and the Straits Times.

    The Classifier Agent uses these to check whether a community incident
    has already been officially reported. You can also use this endpoint
    to see what data has been seeded into the mock database.
    """
    if not is_supabase_configured():
        raise HTTPException(
            status_code=503,
            detail="Supabase database is not configured. See .env.example.",
        )

    reports = get_all_mock_reports()

    return {
        "count": len(reports),
        "reports": reports,
    }
