import json
from typing import TypedDict, Optional, List
from langgraph.graph import StateGraph, START, END
from IPython.display import Image, display
from langchain_core.runnables.graph import CurveStyle, MermaidDrawMethod, NodeStyles

from dotenv import load_dotenv
import os
load_dotenv()

from sklearn.metrics.pairwise import cosine_similarity

from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


CATEGORY_DEFINITIONS = {
    "theft": "stealing, snatch theft, pickpocket, stolen items",
    "vandalism": "graffiti, spray paint, property damage, vandalism",
    "burglary": "break into, forced entry, shop break-in, house intrusion",
    "suspicious": "loitering, suspicious activity, unknown behavior"
}

def get_embedding(text: str):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

CATEGORY_EMBEDDINGS = {
    cat: get_embedding(desc)
    for cat, desc in CATEGORY_DEFINITIONS.items()
}


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

    # ---------- Category via Vector Similarity ----------

    text_embedding = get_embedding(state["raw_text"])

    best_category = None
    best_score = -1

    for cat, emb in CATEGORY_EMBEDDINGS.items():
        score = cosine_similarity([text_embedding], [emb])[0][0]

        if score > best_score:
            best_score = score
            best_category = cat

    category = best_category

    state["messages"].append({
        "agent": "classifier",
        "note": f"Category selected via vector similarity: {category} (score={round(best_score, 3)})"
    })

    # ACTUAL LLM REASONING (CORE)
    # Classifier re-evaluates classification using feedback from Decision Agent
    if feedback_msgs:
        prompt = f"""
        You are a unreported petty crime classification agent for Singapore.

        Text:
        {state["raw_text"]}

        Current classification:
        category = {category}

        Feedback:
        {feedback_msgs}

        Re-evaluate the category and give a better classification.

        Respond ONLY in JSON:
        {{
            "category": "...",
            "llm_reasoning": "..."
        }}
        """

        # Capture LLM Response
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        # LLM JSON TO DICT
        raw = response.choices[0].message.content #GET RAW RESPONSE

        raw = raw.replace("```json", "").replace("```", "").strip() #CLEAN

        try:
            result = json.loads(raw)

            if "category" not in result:
                raise ValueError
            
        except json.JSONDecodeError:
            result = {
                "category": category,  # fallback to previous
                "llm_reasoning": "LLM output invalid, fallback used"
    }

        category = result["category"]

        state["messages"].append({
            "agent": "classifier",
            "llm_reasoning": result["llm_reasoning"]
        })



    # ---------- AUTHENTICITY & SEVERITY SCORE ----------
    # LLM-as-a-Judge (RUBRIC-BASED FEATURE EXTRACTION)
    prompt = f"""
    You are evaluating a petty crime report using a scoring rubric.

    Text:
    {state["raw_text"]}

    Extract whether the following features are present (true/false):

    DETAIL SPECIFICITY:
    - specific_location
    - specific_time
    - specific_action
    - object_or_person
    - consequence

    EVIDENCE QUALITY:
    - firsthand_report
    - clear_description
    - media_mentioned
    - source_link
    - follow_up_details

    CONSISTENCY:
    - no_contradictions
    - time_location_action_align
    - category_matches
    - no_exaggeration

    RISK FLAGS:
    - rumor_language
    - missing_location
    - missing_time
    - ragebait
    - contradiction

    Return ONLY JSON:
    {{
        "specific_location": true/false,
        "specific_time": true/false,
        "specific_action": true/false,
        "object_or_person": true/false,
        "consequence": true/false,

        "firsthand_report": true/false,
        "clear_description": true/false,
        "media_mentioned": true/false,
        "source_link": true/false,
        "follow_up_details": true/false,

        "no_contradictions": true/false,
        "time_location_action_align": true/false,
        "category_matches": true/false,
        "no_exaggeration": true/false,

        "rumor_language": true/false,
        "missing_location": true/false,
        "missing_time": true/false,
        "ragebait": true/false,
        "contradiction": true/false
    }}
    """

    # LLM extracts features based on the above
    # Call LLM for rubric extraction
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.choices[0].message.content

    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        features = json.loads(raw)

        # Basic Validation
        if not isinstance(features, dict):
            raise ValueError

    except json.JSONDecodeError:
        features = {}

        state["messages"].append({
            "agent": "classifier",
            "llm_reasoning": "LLM feature extraction failed, fallback used",
            "raw_output": raw
        })

    # Log successful extraction 
    state["messages"].append({
        "agent": "classifier",
        "reasoning": "Rubric-based feature extraction completed",
        "features": features
    })
    

    # SCORE THE POST
    # DETAIL SPECIFICITY
    detail = (
        0.25 * features.get("specific_location", 0) +
        0.20 * features.get("specific_time", 0) +
        0.25 * features.get("specific_action", 0) +
        0.20 * features.get("object_or_person", 0) +
        0.10 * features.get("consequence", 0)
    )

    # EVIDENCE QUALITY
    evidence = (
        0.30 * features.get("firsthand_report", 0) +
        0.20 * features.get("clear_description", 0) +
        0.25 * features.get("media_mentioned", 0) +
        0.15 * features.get("source_link", 0) +
        0.10 * features.get("follow_up_details", 0)
    )

    # CONSISTENCY
    consistency = (
        0.40 * features.get("no_contradictions", 0) +
        0.30 * features.get("time_location_action_align", 0) +
        0.20 * features.get("category_matches", 0) +
        0.10 * features.get("no_exaggeration", 0)
    )

    # RISK FLAGS
    risk = (
        0.25 * features.get("rumor_language", 0) +
        0.20 * features.get("missing_location", 0) +
        0.15 * features.get("missing_time", 0) +
        0.20 * features.get("ragebait", 0) +
        0.20 * features.get("contradiction", 0)
    )

    # FINAL SCORE
    authenticity_score = (
        0.25 * detail +
        0.25 * evidence +
        0.15 * consistency -
        0.20 * risk
    )

    # ---------- AUTHENTICITY SCORE ----------
    authenticity_score = max(0, min(authenticity_score, 1))

    # ---------- SEVERITY SCORE ----------
    severity = round(
        0.4 * detail +
        0.3 * evidence +
        0.3 * risk,
        2
    )

    # Log Reasoning
    state["messages"].append({
    "agent": "classifier",
    "note": "Rubric-based evaluation applied",
    "features": features
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

    elif state["retry_count"] >= 2:
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

    state["messages"].append({
        "agent": "decision",
        "note": f"Decision: {state['decision']} based on authenticity score {state['authenticity_score']}"
    })

    return state



# =========================================================
# 5. CONDITIONAL EDGE ROUTER
# ---------------------------------------------------------
# where to go AFTER the decision node.
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

    print("\n=== INCIDENT RESULTS ===\n")

    accepted = 0
    rejected = 0

    for result in all_results:
        print("\n=== RAW MESSAGES ===\n")
        print(result["messages"])

        if result["decision"] == "publish":
            accepted += 1
        elif result["decision"] == "reject":
            rejected += 1

        print(f"Incident ID: {result['incident_id']}")
        print(f"Retry Count: {result['retry_count']}")
        print(f"Decision: {result['decision'].upper()}")
        print(f"Category: {result['category']}")
        print(f"Authenticity Score: {round(result['authenticity_score'], 2)}")
        print(f"Severity: {result['severity']}")
        print(f"Location: {result['location']}")
        print(f"Time: {result['time']}")
        print(f"Action: {result['action']}")

        # Show ONLY key reasoning (not spam)
        last_reasoning = None
        for msg in reversed(result["messages"]):
            if "llm_reasoning" in msg:
                last_reasoning = msg["llm_reasoning"]
                break

        if last_reasoning:
            print(f"LLM Reasoning: {last_reasoning}")

        # =========================
        # AI-to-AI INTERACTION LOG
        # (comment this whole block when not needed)
        # =========================

        print("\n Agent Conversation:\n")

        for msg in result["messages"]:
            agent = msg.get("agent", "unknown")

            if "llm_reasoning" in msg:
                print(f"  {agent.capitalize()} (LLM):")
                print(f"   {msg['llm_reasoning']}\n")

            elif "reasoning" in msg:
                print(f"  {agent.capitalize()} (system):")
                print(f"   {msg['reasoning']}\n")

            elif "instruction" in msg:
                print(f"  {agent.capitalize()}")
                print(f"   {msg['instruction']}\n")

            elif "note" in msg:
                print(f"  {agent.capitalize()}:")
                print(f"   {msg['note']}\n")

        print("-" * 40)

    print("\n=== SUMMARY ===\n")

    total = len(all_results)

    print(f"Total Incidents: {total}")
    print(f"Accepted (Published): {accepted}")
    print(f"Rejected: {rejected}")

    if total > 0:
        print(f"Acceptance Rate: {round((accepted / total) * 100, 1)}%")