from __future__ import annotations

from typing import Any

from .state import IncidentState


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

    return {
        "decision": decision,
        "revision_count": revision_count,
        "notes": state["notes"] + [f"Decider set decision={decision}."],
    }
