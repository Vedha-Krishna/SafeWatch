from typing import TypedDict, Optional, List
from langgraph.graph import StateGraph, START, END


class IncidentState(TypedDict):
    post_id: str
    raw_text: str
    candidate: Optional[bool]
    category: Optional[str]
    authenticity_score: Optional[float]
    decision: Optional[str]
    revision_count: int
    notes: List[str]


def crawler_node(state: IncidentState):
    return {
        "candidate": True,
        "notes": state["notes"] + ["Crawler created incident draft."]
    }


def classifier_node(state: IncidentState):
    return {
        "category": "theft",
        "authenticity_score": 0.72,
        "notes": state["notes"] + ["Classifier scored incident."]
    }


def decision_node(state: IncidentState):
    if state["authenticity_score"] < 0.5:
        return {
            "decision": "needs_revision",
            "revision_count": state["revision_count"] + 1,
            "notes": state["notes"] + ["Decision Agent requested revision."]
        }

    return {
        "decision": "publish",
        "notes": state["notes"] + ["Decision Agent approved publish."]
    }


def route_after_decision(state: IncidentState):
    if state["decision"] == "needs_revision" and state["revision_count"] < 2:
        return "crawler"

    return END


graph_builder = StateGraph(IncidentState)

graph_builder.add_node("crawler", crawler_node)
graph_builder.add_node("classifier", classifier_node)
graph_builder.add_node("decision", decision_node)

graph_builder.add_edge(START, "crawler")
graph_builder.add_edge("crawler", "classifier")
graph_builder.add_edge("classifier", "decision")

graph_builder.add_conditional_edges("decision", route_after_decision)

graph = graph_builder.compile()


if __name__ == "__main__":
    result = graph.invoke({
        "post_id": "post_001",
        "raw_text": "My bicycle was stolen outside Bedok MRT last night.",
        "candidate": None,
        "category": None,
        "authenticity_score": None,
        "decision": None,
        "revision_count": 0,
        "notes": []
    })

    print(result)