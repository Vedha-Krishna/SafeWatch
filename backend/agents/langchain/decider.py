from __future__ import annotations

import logging
from typing import Any

from .state import IncidentState

try:
    from backend.db.incidents import insert_incident
    from backend.db.supabase import is_supabase_configured
except ImportError:
    from db.incidents import insert_incident
    from db.supabase import is_supabase_configured

logger = logging.getLogger(__name__)

_DECISION_TO_STATUS = {
    "publish": "processed",
    "reject": "rejected",
    "needs_revision": "needs_revision",
}


def decision_node(state: IncidentState) -> dict[str, Any]:
    is_publishable = (
        state["authenticity_score"] is not None
        and state["authenticity_score"] >= 0.7
        and state["category"] not in (None, "unknown")
    )

    if is_publishable:
        decision = "publish"
        revision_count = state["revision_count"]
    else:
        decision = "needs_revision"
        revision_count = state["revision_count"] + 1

    if is_supabase_configured():
        try:
            record = {
                "source_platform": "other",
                "raw_text": state["raw_text"],
                # status → incident_queue; decision → incident_decisions
                # category/authenticity_score → incident_analysis
                # agent_notes → incident_agent_messages rows
                "status":            _DECISION_TO_STATUS.get(decision, decision),
                "decision":          decision,
                "category":          state["category"],
                "authenticity_score": state["authenticity_score"],
                "agent_notes":       state["notes"],
            }
            insert_incident(record)
        except Exception as exc:
            logger.error("Supabase write failed for post %s: %s", state["post_id"], exc)

    return {
        "decision": decision,
        "revision_count": revision_count,
        "notes": state["notes"] + [f"Decider set decision={decision}."],
    }
