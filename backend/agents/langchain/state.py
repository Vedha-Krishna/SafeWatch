from __future__ import annotations

from typing import Optional, TypedDict


class IncidentState(TypedDict):
    post_id: str
    raw_text: str
    candidate: Optional[bool]
    category: Optional[str]
    authenticity_score: Optional[float]
    decision: Optional[str]
    revision_count: int
    notes: list[str]
