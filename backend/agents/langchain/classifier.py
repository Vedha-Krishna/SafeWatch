from __future__ import annotations

from typing import Any

from .state import IncidentState


def classifier_node(state: IncidentState) -> dict[str, Any]:
    text = state["raw_text"].lower()

    if any(keyword in text for keyword in ("snatch", "stolen", "stole", "steal")):
        category = "theft"
        authenticity_score = 0.78
    elif any(keyword in text for keyword in ("vandal", "graffiti", "spray paint")):
        category = "vandalism"
        authenticity_score = 0.64
    elif any(keyword in text for keyword in ("harass", "threat", "intimidat")):
        category = "harassment"
        authenticity_score = 0.66
    else:
        category = "unknown"
        authenticity_score = 0.35

    return {
        "category": category,
        "authenticity_score": authenticity_score,
        "notes": state["notes"] + [
            f"Classifier assigned category={category} authenticity={authenticity_score:.2f}."
        ],
    }
