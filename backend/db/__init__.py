"""
Database package for PettyCrimeSG.

This package provides all the functions needed to read from and write to
the Supabase database. Other parts of the application (agents, API routes)
should import from here rather than from the individual module files.

WHY IMPORT FROM HERE:
    Instead of writing:
        from backend.db.incidents import get_all_incidents
        from backend.db.feedback import insert_feedback

    You can write the simpler:
        from backend.db import get_all_incidents, insert_feedback

    This keeps imports clean and means internal file reorganization
    won't break other files.

CHECKING IF DATABASE IS AVAILABLE:
    Before calling any database function, check is_supabase_configured() to see
    if the environment variables have been set. This allows the app to fall back
    to JSON files for local development without a Supabase project.

    Example:
        from backend.db import is_supabase_configured, get_published_incidents

        if is_supabase_configured():
            incidents = get_published_incidents()
        else:
            incidents = load_from_json_file()
"""

# -----------------------------------------------------------------------
# CONNECTION — Client setup and configuration check
# -----------------------------------------------------------------------
from .supabase import get_supabase_client, is_supabase_configured

# -----------------------------------------------------------------------
# INCIDENTS — Main incident table operations
# -----------------------------------------------------------------------
from .incidents import (
    # Save a new incident to the database
    insert_incident,

    # Read one incident by its ID
    get_incident_by_id,

    # Read multiple incidents (with optional status filter)
    get_all_incidents,

    # Shortcut: read only published incidents (for the public map)
    get_published_incidents,

    # Shortcut: read only candidate incidents (waiting for classification)
    get_candidate_incidents,

    # Update any fields of an existing incident
    update_incident,

    # Shortcut: update just the status field
    update_incident_status,

    # Add a note to an incident's agent_notes array
    append_agent_note,
)

# -----------------------------------------------------------------------
# FEEDBACK — Agent-to-agent communication log
# -----------------------------------------------------------------------
from .feedback import (
    # Send a new feedback message from one agent to another
    insert_feedback,

    # Read all feedback messages for a specific incident
    get_feedback_for_incident,

    # Read unresolved (pending) feedback — used by agents to check their queue
    get_unresolved_feedback,

    # Read ALL feedback (both resolved and unresolved)
    get_all_feedback,

    # Mark a single feedback message as resolved
    mark_feedback_resolved,

    # Mark ALL feedback for an incident as resolved at once
    resolve_all_feedback_for_incident,
)

# -----------------------------------------------------------------------
# MOCK OFFICIAL REPORTS — Stand-in for real official crime databases
# -----------------------------------------------------------------------
from .mock_reports import (
    # Get all mock official reports
    get_all_mock_reports,

    # Check if a community incident was already officially reported
    find_similar_official_report,

    # Get all official reports for a specific crime category
    get_reports_by_category,

    # Add a single mock report (for seeding test data)
    insert_mock_report,

    # Add multiple mock reports at once (bulk seed)
    seed_mock_reports,
)

# -----------------------------------------------------------------------
# __all__ tells Python exactly what to include when someone does:
#   from backend.db import *
# It also serves as a reference for what this package provides.
# -----------------------------------------------------------------------
__all__ = [
    # Connection
    "get_supabase_client",
    "is_supabase_configured",

    # Incidents
    "insert_incident",
    "get_incident_by_id",
    "get_all_incidents",
    "get_published_incidents",
    "get_candidate_incidents",
    "update_incident",
    "update_incident_status",
    "append_agent_note",

    # Feedback
    "insert_feedback",
    "get_feedback_for_incident",
    "get_unresolved_feedback",
    "get_all_feedback",
    "mark_feedback_resolved",
    "resolve_all_feedback_for_incident",

    # Mock official reports
    "get_all_mock_reports",
    "find_similar_official_report",
    "get_reports_by_category",
    "insert_mock_report",
    "seed_mock_reports",
]
