from __future__ import annotations

"""
incidents.py — Database operations for the normalised incidents schema.

Reads use the `incident_full` view which pre-joins all five pipeline tables:
    incidents            core identity + raw content
    incident_queue       workflow/pipeline state
    incident_analysis    classifier output
    incident_locations   lat/lng/location
    incident_decisions   decision agent output

Writes are routed to individual tables based on the column names supplied.
`incident_agent_messages` is written via append_agent_note().

HOW THIS FITS INTO THE SYSTEM:
    Crawler Agent  → calls insert_incident()        to save a new draft
    Cleaner Agent  → writes directly to satellite tables (bypasses this layer)
    Classifier     → calls update_incident()        to add analysis columns
    Decision Agent → calls update_incident()        to add decision columns
    FastAPI        → calls get_all_incidents()      to serve the frontend
    Frontend map   → reads processed incidents via the API
"""

import hashlib

from .supabase import get_supabase_client

# Table/view names
INCIDENTS_TABLE  = "incidents"
QUEUE_TABLE      = "incident_queue"
ANALYSIS_TABLE   = "incident_analysis"
LOCATION_TABLE   = "incident_locations"
DECISIONS_TABLE  = "incident_decisions"
MESSAGES_TABLE   = "incident_agent_messages"
FULL_VIEW        = "incident_full"

_AGENT_ROLE_ALIASES = {
    "crawler": "crawler",
    "cleaner": "cleaner",
    "classifier": "classifier",
    "decision": "decision_agent",
    "decider": "decision_agent",
    "decision_agent": "decision_agent",
}

_SOURCE_PLATFORM_ALIASES = {
    "reddit": "reddit",
    "facebook": "facebook",
    "x": "x",
    "twitter": "x",
    "hardwarezone": "hardwarezone",
    "telegram": "telegram",
    "other": "other",
    "mock": "other",
    "mock_forum": "other",
    "mock_social": "other",
    "mock_reddit": "reddit",
    "langgraph_pipeline": "other",
}

_SOURCE_TYPE_ALIASES = {
    "post": "post",
    "comment": "comment",
}

_WORKFLOW_STATUS_ALIASES = {
    "raw": "raw",
    "queued": "queued",
    "in_progress": "in_progress",
    "cleaned": "cleaned",
    "classifying": "classifying",
    "classified": "classified",
    "candidate": "candidate",
    "deciding": "deciding",
    "processed": "processed",
    "published": "processed",
    "rejected": "rejected",
    "failed": "failed",
    "merged": "merged",
    "needs_revision": "needs_revision",
}

_TOPIC_BUCKET_ALIASES = {
    "singapore_news": "singapore_news",
    "singapore_viral": "singapore_viral",
    "other": "other",
}

_REPORT_STATUS_ALIASES = {
    "reported": "reported",
    "unreported": "unreported",
    "unknown": "unknown",
}


def _normalise_agent_role(value: object, default: str = "crawler") -> str:
    role = str(value or "").strip().lower().replace(" ", "_")
    return _AGENT_ROLE_ALIASES.get(role, default)


def _normalise_enum_value(
    value: object,
    aliases: dict[str, str],
    field_name: str,
    *,
    allow_none: bool = False,
) -> object:
    if value is None and allow_none:
        return None
    key = str(value or "").strip().lower().replace(" ", "_")
    if key in aliases:
        return aliases[key]
    raise ValueError(f"Invalid {field_name}: {value!r}")


def _normalise_core_payload(data: dict) -> dict:
    out = dict(data)
    if "source_platform" in out:
        out["source_platform"] = _normalise_enum_value(
            out["source_platform"],
            _SOURCE_PLATFORM_ALIASES,
            "incidents.source_platform",
        )
    if "source_type" in out:
        out["source_type"] = _normalise_enum_value(
            out["source_type"],
            _SOURCE_TYPE_ALIASES,
            "incidents.source_type",
            allow_none=True,
        )
    return out


def _normalise_queue_payload(data: dict) -> dict:
    out = dict(data)
    if "status" in out:
        out["status"] = _normalise_enum_value(
            out["status"],
            _WORKFLOW_STATUS_ALIASES,
            "incident_queue.status",
        )
    for field in ("current_agent", "next_agent"):
        if field in out and out[field] is not None:
            out[field] = _normalise_agent_role(out[field])
    return out


def _normalise_analysis_payload(data: dict) -> dict:
    out = dict(data)
    if "topic_bucket" in out:
        out["topic_bucket"] = _normalise_enum_value(
            out["topic_bucket"],
            _TOPIC_BUCKET_ALIASES,
            "incident_analysis.topic_bucket",
            allow_none=True,
        )
    return out


def _normalise_decision_payload(data: dict) -> dict:
    out = dict(data)
    if "report_status" in out:
        out["report_status"] = _normalise_enum_value(
            out["report_status"],
            _REPORT_STATUS_ALIASES,
            "incident_decisions.report_status",
            allow_none=True,
        )
    return out


def _agent_role_from_note(text: str) -> str:
    first_word = text.strip().split(" ", 1)[0].split(":", 1)[0]
    return _normalise_agent_role(first_word)


# Column routing — maps each column to its owner table
_INCIDENTS_COLS = frozenset({
    "source_platform", "source_type", "source_item_id", "parent_source_item_id",
    "source_url", "raw_text", "language_code", "timestamp_text", "normalized_time",
    "duplicate_of", "dedupe_key",
})
_QUEUE_COLS = frozenset({
    "status", "locked_by", "locked_at", "retry_count", "last_error",
    "current_agent", "next_agent", "available_at", "max_attempts",
})
_ANALYSIS_COLS = frozenset({
    "cleaned_content", "topic_bucket", "topic_similarity_score",
    "category", "authenticity_score", "severity", "category_score",
    "extracted_entities", "candidate_scores", "matched_signals",
})
_LOCATION_COLS = frozenset({"location_text", "latitude", "longitude"})
_DECISION_COLS  = frozenset({"decision", "decision_reason", "report_status"})


def _route(data: dict, cols: frozenset) -> dict:
    return {k: v for k, v in data.items() if k in cols}


def _make_dedupe_key(data: dict) -> str:
    platform = str(data.get("source_platform") or "")
    item_id  = str(data.get("source_item_id") or "")
    if platform and item_id:
        raw = f"{platform}:{item_id}"
    else:
        raw = str(data.get("raw_text") or data.get("source_url") or str(id(data)))
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


# -----------------------------------------------------------------------
# CREATE
# -----------------------------------------------------------------------

def insert_incident(incident_data: dict) -> dict:
    """
    Save a new incident across all normalised tables.

    Accepts the same flat dict as the old single-table version.
    Internally routes each field to the correct table.

    Handles legacy callers that pass:
        agent_notes  (list[str])  → rows in incident_agent_messages
        status       (str)        → incident_queue.status
        decision     (str)        → incident_decisions.decision
        category etc.             → incident_analysis
        location_text etc.        → incident_locations

    Returns the fully joined record from the incident_full view.
    """
    client = get_supabase_client()

    # 1. Core incidents row (required)
    core = _normalise_core_payload(_route(incident_data, _INCIDENTS_COLS))
    if "dedupe_key" not in core:
        core["dedupe_key"] = _make_dedupe_key(incident_data)
    resp = client.table(INCIDENTS_TABLE).insert(core).execute()
    incident_id: str = resp.data[0]["incident_id"]

    # 2. Queue row (always created alongside every incident)
    queue = _route(incident_data, _QUEUE_COLS)
    queue["incident_id"] = incident_id
    queue.setdefault("status", "raw")
    queue = _normalise_queue_payload(queue)
    client.table(QUEUE_TABLE).insert(queue).execute()

    # 3. Analysis row (only if classifier fields are present)
    analysis = _normalise_analysis_payload(_route(incident_data, _ANALYSIS_COLS))
    if analysis:
        analysis["incident_id"] = incident_id
        client.table(ANALYSIS_TABLE).insert(analysis).execute()

    # 4. Location row (only if location fields are present)
    location = _route(incident_data, _LOCATION_COLS)
    if location:
        location["incident_id"] = incident_id
        client.table(LOCATION_TABLE).insert(location).execute()

    # 5. Decision row (only if decision fields are present)
    decision = _normalise_decision_payload(_route(incident_data, _DECISION_COLS))
    if decision:
        decision["incident_id"] = incident_id
        client.table(DECISIONS_TABLE).insert(decision).execute()

    # 6. agent_notes list → message rows (backward compat with legacy callers)
    notes = incident_data.get("agent_notes") or []
    for seq, note in enumerate(notes):
        text = note if isinstance(note, str) else str(note)
        client.table(MESSAGES_TABLE).insert({
            "incident_id":    incident_id,
            "agent":          _agent_role_from_note(text),
            "sequence_order": seq,
            "message_type":   "note",
            "summary":        text,
        }).execute()

    record = get_incident_by_id(incident_id)
    assert record is not None
    return record


# -----------------------------------------------------------------------
# READ
# -----------------------------------------------------------------------

def get_incident_by_id(incident_id: str) -> dict | None:
    """Retrieve a single incident (all fields) from the incident_full view."""
    client = get_supabase_client()
    response = (
        client
        .table(FULL_VIEW)
        .select("*")
        .eq("incident_id", incident_id)
        .execute()
    )
    return response.data[0] if response.data else None


def get_all_incidents(
    status_filter: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """
    Retrieve incidents from the incident_full view.

    status_filter filters on incident_queue.status exposed through the view.
    Valid values depend on the workflow_status_type enum in the DB.
    """
    client = get_supabase_client()
    query = client.table(FULL_VIEW).select("*")
    if status_filter is not None:
        query = query.eq("status", status_filter)
    query = query.order("created_at", desc=True).limit(limit)
    return query.execute().data


def get_published_incidents(limit: int = 100) -> list[dict]:
    """Retrieve incidents approved for the public map (status='processed')."""
    return get_all_incidents(status_filter="processed", limit=limit)


def get_candidate_incidents(limit: int = 100) -> list[dict]:
    """Retrieve incidents flagged by the Crawler awaiting classification."""
    return get_all_incidents(status_filter="candidate", limit=limit)


# -----------------------------------------------------------------------
# UPDATE
# -----------------------------------------------------------------------

def update_incident(incident_id: str, updates: dict) -> dict:
    """
    Update one or more fields of an existing incident.

    Routes each field to the correct normalised table automatically.
    Satellite tables (analysis, location, decision) are upserted so callers
    don't need to worry about whether the row already exists.

    Returns the updated record from the incident_full view.
    """
    client = get_supabase_client()

    core     = _normalise_core_payload(_route(updates, _INCIDENTS_COLS))
    queue    = _normalise_queue_payload(_route(updates, _QUEUE_COLS))
    analysis = _normalise_analysis_payload(_route(updates, _ANALYSIS_COLS))
    location = _route(updates, _LOCATION_COLS)
    decision = _normalise_decision_payload(_route(updates, _DECISION_COLS))

    if core:
        client.table(INCIDENTS_TABLE).update(core).eq("incident_id", incident_id).execute()
    if queue:
        client.table(QUEUE_TABLE).update(queue).eq("incident_id", incident_id).execute()
    if analysis:
        client.table(ANALYSIS_TABLE).upsert({"incident_id": incident_id, **analysis}).execute()
    if location:
        client.table(LOCATION_TABLE).upsert({"incident_id": incident_id, **location}).execute()
    if decision:
        client.table(DECISIONS_TABLE).upsert({"incident_id": incident_id, **decision}).execute()

    record = get_incident_by_id(incident_id)
    assert record is not None
    return record


def update_incident_status(incident_id: str, new_status: str) -> dict:
    """Change just the status field (writes to incident_queue)."""
    return update_incident(incident_id, {"status": new_status})


def append_agent_note(
    incident_id: str,
    note: str,
    existing_notes: list[str],  # kept for backward compat; no longer read
) -> dict:
    """
    Add a note to an incident's agent message log.

    Inserts a row into incident_agent_messages. The `existing_notes` parameter
    is kept for backward compatibility but is no longer needed — sequence numbers
    are determined from the DB directly.
    """
    client = get_supabase_client()

    resp = (
        client
        .table(MESSAGES_TABLE)
        .select("sequence_order")
        .eq("incident_id", incident_id)
        .order("sequence_order", desc=True)
        .limit(1)
        .execute()
    )
    next_seq: int = (resp.data[0]["sequence_order"] + 1) if resp.data else 0

    # Parse "Agent Name: message text" convention used by callers
    agent   = _agent_role_from_note(note)
    summary = note
    if ": " in note:
        prefix, summary = note.split(": ", 1)
        agent = _normalise_agent_role(prefix)

    client.table(MESSAGES_TABLE).insert({
        "incident_id":    incident_id,
        "agent":          agent,
        "sequence_order": next_seq,
        "message_type":   "note",
        "summary":        summary,
    }).execute()

    record = get_incident_by_id(incident_id)
    assert record is not None
    return record
