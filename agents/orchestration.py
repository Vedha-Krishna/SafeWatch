import json
from typing import TypedDict, Optional, List
from langgraph.graph import StateGraph, START, END
from IPython.display import Image, display
from langchain_core.runnables.graph import CurveStyle, MermaidDrawMethod, NodeStyles


class State(TypedDict):
    ## CRAWLER FIELDS
    incident_id: str
    source_platform: str
    source_url: str
    raw_text: str

    ## CLASSIFIER FIELDS
    category: Optional[str]
    authenticity_score: Optional[float]
    severity: Optional[float]

    location: Optional[str]
    time: Optional[str]
    action: Optional[str]



    ## DECISION FIELDS
    decision: Optional[str]


    ## Message
    agent_notes: Optional[str]


def crawler_node(State):

    State["incident_id"] = 1
    State["source_platform"] = "mock_Reddit"
    State["source_url"] = "mock_reddit.com"
    State["agent_notes"] = "Crawler extracted basic fields"

    return State


def classifier_node(State):
    text = State["raw_text"].lower()

    location = None
    time = None
    action = None
    
    if "bugis" in text:
        location = "Bugis"
    elif "toa payoh" in text:
        location = "Toa Payoh"

    if "8pm" in text:
        time = "8pm"
    elif "9pm" in text:
        time = "9pm"

    if "snatch" in text or "snatched" in text:
        action = "snatch theft"
    elif "stole" in text or "steal" in text:
        action = "theft"
    elif "vandal" in text or "spray paint" in text:
        action = "vandalism"

    State["location"] = location
    State["time"] = time
    State["action"] = action


    if State["action"] == "snatch theft":
        State["category"] = "theft"
        State["severity"] = 0.7
    elif State["action"] == "theft":
        State["category"] = "theft"
        State["severity"] = 0.6
    elif State["action"] == "vandalism":
        State["category"] = "vandalism"
        State["severity"] = 0.4
    else:
        State["category"] = "unknown"
        State["severity"] = 0.2

    if State["location"] and State["time"] and State["action"]:
        State["authenticity_score"] = 0.8
    else:
        State["authenticity_score"] = 0.3

    State["agent_notes"] = "Classifier assigned category and scores"

    return State


def decision_node(State):
    if (
        State["authenticity_score"] is not None
        and State["authenticity_score"] >= 0.7
        and State["category"] != "unknown"
    ):
        State["decision"] = "publish"
    else:
        State["decision"] = "needs_revision"

    State["agent_notes"] = f"Decision agent set decision to {State['decision']}"
    return State

def edge_after_decision(State):
    if State["decision"] == "needs_revision":
        return "crawler"
    return END


## State JSON
graph_builder = StateGraph(State)

## NODES
graph_builder.add_node("crawler", crawler_node)
graph_builder.add_node("classifier", classifier_node)
graph_builder.add_node("decision", decision_node)

## EDGES
graph_builder.add_edge(START, "crawler")
graph_builder.add_edge("crawler", "classifier")
graph_builder.add_edge("classifier", "decision")
graph_builder.add_edge("decision", END)

## CONDTIONAL EDGES
graph_builder.add_conditional_edges("decision", edge_after_decision)

## COMPILE
graph = graph_builder.compile()


## Display Graph
# png_data = graph.get_graph().draw_mermaid_png()

# with open("graph.png", "wb") as f:
#     f.write(png_data)

# print("Saved as graph.png")

with open("data/mock_posts.json", "r", encoding="utf-8") as f:
    mock_posts = json.load(f)

initial_State = mock_posts

result = graph.invoke(initial_State)

print(result)