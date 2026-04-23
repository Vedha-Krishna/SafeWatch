import json
from typing import TypedDict, Optional, List
from langgraph.graph import StateGraph, START, END
from IPython.display import Image, display
from langchain_core.runnables.graph import CurveStyle, MermaidDrawMethod, NodeStyles



# =========================================================
# 1. SHARED STATE
# ---------------------------------------------------------
# This is the data structure that moves through the graph.
# Each node reads from it and returns updates to it.
# =========================================================
class State(TypedDict):
    ## CRAWLER FIELDS
    incident_id: int
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
    messages: List[dict]


    ## Retry Counter
    retry_count: int

# =========================================================
# 2. CRAWLER NODE
# ---------------------------------------------------------
# For now this is NOT a real web crawler.
# It acts like a lightweight extraction agent:
# - reads raw_text
# - extracts simple location / time / action signals
# - returns updated fields
# =========================================================
def crawler_node(state: State) -> dict:

    # MOCK: Fake data source (not real scraping or tool usage)
    state["source_platform"] = "mock_Reddit"
    state["source_url"] = "mock_reddit.com"

    # MOCK: Logging step (simulates agent output message)
    state["messages"].append({
        "agent": "crawler",
        "note": "Crawler extracted basic fields"
    })
    state["retry_count"] += 1

    return state



# =========================================================
# 3. CLASSIFIER NODE
# ---------------------------------------------------------
# This node assigns:
# - location extraction
# - time extraction
# - action extraction
# - category scoring
# - authenticity scoring
# - severity scoring
#
# For now this is still mock logic.
# Later you can replace this with:
# - rule-based scoring
# - embeddings
# - LLM scoring
# =========================================================
def classifier_node(state: State) -> dict:
    text = state["raw_text"].lower()

    # Get messages meant for classifier
    # MOCK: Simulating agent receiving feedback (instead of real LLM reading messages)
    feedback_msgs = [
        m for m in state["messages"]
        if m.get("feedback_to") == "classifier"
    ]

    # ---------- Extraction ----------
    location = None
    time = None
    action = None

    if "bugis" in text:
        location = "Bugis MRT"
    elif "toa payoh" in text:
        location = "Toa Payoh"
    elif "jurong east" in text:
        location = "Jurong East"
    elif "tampines" in text:
        location = "Tampines"

    if "8pm" in text:
        time = "8pm"
    elif "9pm" in text:
        time = "9pm"
    elif "10pm" in text:
        time = "10pm"
    elif "morning" in text:
        time = "morning"

    if "snatch" in text or "snatched" in text:
        action = "snatch theft"
    elif "stole" in text or "steal" in text or "stolen" in text:
        action = "theft"
    elif "vandal" in text or "spray paint" in text:
        action = "vandalism"
    elif "broke into" in text:
        action = "break-in"

    # ---------- Category + Severity ----------
    # MOCK: Deterministic mapping (real system would use LLM or model)
    category = "unknown"
    severity = 0.2

    if action == "snatch theft":
        category = "theft"
        severity = 0.8
    elif action == "theft":
        category = "theft"
        severity = 0.6
    elif action == "vandalism":
        category = "vandalism"
        severity = 0.4
    elif action == "break-in":
        category = "break-in"
        severity = 0.9

    # MOCK LLM REASONING (CORE SIMULATION)
    # Simulates classifier "rethinking" based on feedback from another agent
    if feedback_msgs:
        if category == "unknown":
            category = "suspicious"

    # ---------- Authenticity Score ----------
    # MOCK: Rule-based scoring (simulating confidence calculation)
    score = 0.0

    if location:
        score += 0.25
    if time:
        score += 0.25
    if action:
        score += 0.25

    eyewitness_terms = ["saw", "someone", "near", "around"]
    if any(term in text for term in eyewitness_terms):
        score += 0.15

    concrete_terms = ["phone", "wallet", "shop", "station", "mrt", "bike"]
    if any(term in text for term in concrete_terms):
        score += 0.10

    authenticity_score = round(min(score, 1.0), 2)

    # MOCK LLM REASONING (SECONDARY EFFECT)
    # Simulates increased confidence after "re-evaluation"
    if feedback_msgs:
        authenticity_score = min(authenticity_score + 0.15, 1.0)

    # MOCK: Agent explaining its reasoning (instead of real LLM explanation)
    ## Message for next agent
    state["messages"].append({
        "agent": "classifier",
        "note": f"location={location}, time={time}, action={action}, category={category}, authenticity={authenticity_score}"
    })

    return {
        "location": location,
        "time": time,
        "action": action,
        "category": category,
        "authenticity_score": authenticity_score,
        "severity": severity,
        "messages": state["messages"]
    }



# =========================================================
# 4. DECISION NODE
# ---------------------------------------------------------
# Final decision:
# - publish
# - needs_retry
# - reject
#
# Logic here is intentionally simple and explainable.
# =========================================================
def decision_node(state: State) -> dict:

    # MOCK: Hardcoded decision logic (instead of LLM deciding)
    if (
        state["authenticity_score"] is not None
        and state["authenticity_score"] >= 0.7
        and state["category"] != "unknown"
    ):
        state["decision"] = "publish"

    elif state["retry_count"] >= 5:
        state["decision"] = "reject"

    else:
        # MOCK LLM REASONING (CRITIQUE STEP)
        # Simulates decision agent analyzing output and giving feedback
        state["messages"].append({
            "agent": "decision",
            "feedback_to": "classifier",
            "instruction": "Improve classification using stronger evidence",
            "reason": f"Low authenticity score: {state['authenticity_score']}"
        })
        state["decision"] = "needs_retry"

    return state



# =========================================================
# 5. CONDITIONAL EDGE ROUTER
# ---------------------------------------------------------
# This determines where to go AFTER the decision node.
#
# If "needs_retry":
# - increment retry_count
# - go back to crawler
#
# Otherwise:
# - end graph
#
# Using Literal helps LangGraph understand the possible routes.
# =========================================================
def edge_after_decision(state: State) -> dict:
    if state["decision"] == "needs_retry":
        return "crawler"
    return END



# =========================================================
# 6. BUILD GRAPH
# =========================================================
## state JSON
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




# =========================================================
# 7. HELPER: PREPARE INITIAL STATE
# ---------------------------------------------------------
# Your JSON file only needs to store raw/mock data.
# This function fills in the empty runtime fields.
# =========================================================
def prepare_initial_state(post: dict) -> State:
    return {
        "incident_id": post["incident_id"],
        "source_platform": post["source_platform"],
        "source_url": post["source_url"],
        "raw_text": post["raw_text"],

        "location": None,
        "time": None,
        "action": None,

        "category": None,
        "authenticity_score": None,
        "severity": None,

        "decision": None,

        "messages": [],
        "retry_count": 0,
    }



# =========================================================
# 8. RUN ONE POST THROUGH THE PIPELINE
# ---------------------------------------------------------
# =========================================================
def run_pipeline_for_1_post(post: dict) -> State:
    state = prepare_initial_state(post)

    result = graph.invoke(state)

    return result


# =========================================================
# 9. MAIN
# ---------------------------------------------------------
# Load mock posts, run each one, print results.
# =========================================================
if __name__ == "__main__":
    with open("data/mock_posts.json", "r", encoding="utf-8") as f:
        mock_posts = json.load(f)

    all_results = []

    for i, post in enumerate(mock_posts, start=1):
        post["incident_id"] = i

        final_state = run_pipeline_for_1_post(post)
        all_results.append(final_state)

    print("\n=== FINAL RESULTS ===\n")
    for result in all_results:
        print(f"Retry Count: {result['retry_count']}")
        print(f"Incident ID: {result['incident_id']}")
        print(f"Decision: {result['decision']}")
        print(f"Category: {result['category']}")
        print(f"Authenticity: {result['authenticity_score']}")
        print(f"Severity: {result['severity']}")
        print(f"Location: {result['location']}")
        print(f"Time: {result['time']}")
        print(f"Action: {result['action']}")
        print("Agent Notes:")
        for note in result["messages"]:
            print(f"  - {note}")
        print("-" * 50)