from __future__ import annotations

from typing import Any

from .state import IncidentState


def cleaner_node(state: IncidentState) -> dict[str, Any]:
    normalized_text = " ".join(state["raw_text"].split())

    return {
        "raw_text": normalized_text,
        "notes": state["notes"] + ["Cleaner normalized whitespace in raw incident text."],
    }
