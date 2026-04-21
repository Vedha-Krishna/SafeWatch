from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from .classifier import classifier_node
from .cleaner import cleaner_node
from .decider import decision_node
from .state import IncidentState


def crawler_node(state: IncidentState) -> dict[str, Any]:
    return {
        "candidate": True,
        "notes": state["notes"] + ["Crawler prepared candidate incident draft."],
    }


def route_after_decision(state: IncidentState) -> str:
    if state["decision"] == "needs_revision" and state["revision_count"] < 2:
        return "cleaner"
    return END


def build_graph() -> StateGraph:
    graph_builder = StateGraph(IncidentState)

    graph_builder.add_node("crawler", crawler_node)
    graph_builder.add_node("cleaner", cleaner_node)
    graph_builder.add_node("classifier", classifier_node)
    graph_builder.add_node("decider", decision_node)

    graph_builder.add_edge(START, "crawler")
    graph_builder.add_edge("crawler", "cleaner")
    graph_builder.add_edge("cleaner", "classifier")
    graph_builder.add_edge("classifier", "decider")
    graph_builder.add_conditional_edges("decider", route_after_decision)

    return graph_builder.compile()


graph = build_graph()


def run_workflow(state: IncidentState) -> IncidentState:
    return graph.invoke(state)


if __name__ == "__main__":
    result = run_workflow(
        {
            "post_id": "post_001",
            "raw_text": "  My bicycle was stolen outside Bedok MRT last night.  ",
            "candidate": None,
            "category": None,
            "authenticity_score": None,
            "decision": None,
            "revision_count": 0,
            "notes": [],
        }
    )

    print(result)
