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


## Define and Embed Categories
def get_embedding(text: str):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding


CATEGORY_DEFINITIONS = {
    "theft": [
        "A person stole someone else's belongings without consent.",
        "Unattended property was taken without force.",
        "Items were stolen from a victim, shop, or public place.",
        "Property was dishonestly taken without unlawful entry or physical violence."
    ],
    "burglary": [
        "A suspect broke into a house, shop, or office to steal or commit an offense.",
        "There was forced entry into a premises.",
        "Someone unlawfully entered a building and stole property.",
        "A break-in or house intrusion occurred."
    ],
    "robbery": [
        "Property was taken directly from a person using force, intimidation, or threat.",
        "A victim was threatened or attacked and had belongings taken.",
        "A mugging or forceful snatch theft occurred."
    ],
    "assault": [
        "A person physically attacked another person.",
        "The victim was punched, kicked, slapped, or hit.",
        "There was bodily violence against a person.",
        "Someone was beaten or attacked during a dispute."
    ],
    "vandalism": [
        "Property was intentionally damaged or defaced.",
        "Someone spray-painted, smashed, or damaged public or private property.",
        "A vehicle, wall, or building was vandalized.",
        "Intentional property damage occurred."
    ],
    "scam_fraud": [
        "A person was deceived to obtain money, data, or benefit.",
        "A scam, phishing attempt, or fraudulent transaction occurred.",
        "Someone impersonated another person or entity for dishonest gain.",
        "The victim was cheated through deception rather than physical theft."
    ],
    "harassment_threat": [
        "A person threatened, harassed, intimidated, or stalked another person.",
        "There was abusive or threatening behavior without confirmed physical attack.",
        "The victim faced intimidation, verbal threats, or persistent harassment."
    ],
    "sexual_offense": [
        "A sexual offense or sexual exploitation incident occurred.",
        "There was molestation, voyeurism, trafficking for sexual exploitation, or non-consensual sexual conduct.",
        "The incident involved sexual misconduct or abuse."
    ],
    "suspicious_activity": [
        "Concerning or unusual behavior was observed, but no clear offense was confirmed.",
        "A suspicious person was loitering, lurking, peeping, or trying door handles.",
        "The activity suggested risk, but the exact crime was unclear.",
        "Suspicious behavior was reported without enough evidence for a more specific crime label."
    ],
    "public_disorder": [
        "There was disorderly or disruptive behavior affecting public peace.",
        "A fight, aggressive disturbance, or serious nuisance occurred in public.",
        "The incident involved public disorder rather than property crime or deception."
    ]
}

CATEGORY_EMBEDDINGS = {
    cat: [get_embedding(text) for text in prototypes]
    for cat, prototypes in CATEGORY_DEFINITIONS.items()
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
    incident_summary: Optional[str]


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

    return state



# =========================================================
# 3. CLASSIFIER NODE
# ---------------------------------------------------------
# This node performs:
# - llm rule-based extraction
# - vector similarity category selection
# - LLM reasoning
# - rubric-based authenticity scoring
# - severity scoring
# =========================================================
def classifier_node(state: State) -> dict:
    text = state["raw_text"].lower()

    # Get messages meant for classifier
    # MOCK: Simulating agent receiving feedback (instead of real LLM reading messages)
    feedback_msgs = [
        m for m in state["messages"]
        if m.get("feedback_to") == "classifier"
    ]

    # ---------- EXTRACT LOCATION, TIME, ACTION ----------
    location = None
    time = None
    action = None
    incident_summary = None

    prompt = f"""
    You are an extraction agent for petty crime reports in Singapore.

    Text:
    {state["raw_text"]}

    Extract the following fields from the text:
    - location
    - time
    - action
    - incident_summary

    Rules:
    - Use null if a field is not clearly present
    - Keep values short and literal
    - Do not infer extra details not supported by the text
    - incident_summary should be one short sentence capturing what happened

    Respond ONLY in JSON:
    {{
        "location": "... or null",
        "time": "... or null",
        "action": "... or null",
        "incident_summary": "... or null"
    }}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.choices[0].message.content
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        result = json.loads(raw)

        if not isinstance(result, dict):
            raise ValueError

    except (json.JSONDecodeError, ValueError):
        result = {
            "location": None,
            "time": None,
            "action": None,
            "incident_summary": None
        }

        state["messages"].append({
            "agent": "classifier",
            "note": "LLM extraction failed, fallback used",
            "raw_output": raw
        })

    location = result.get("location")
    time = result.get("time")
    action = result.get("action")
    incident_summary = result.get("incident_summary")

    state["messages"].append({
        "agent": "classifier",
        "reasoning": "LLM extraction completed",
        "extracted_fields": {
            "location": location,
            "time": time,
            "action": action,
            "incident_summary": incident_summary
        }
    })

    # ---------- Category via Vector Similarity ----------

    incident_text_for_embedding = incident_summary or state["raw_text"]
    incident_embedding = get_embedding(incident_text_for_embedding)

    candidate_scores = {}

    for cat, prototype_embs in CATEGORY_EMBEDDINGS.items():
        scores = [
            cosine_similarity([incident_embedding], [emb])[0][0]
            for emb in prototype_embs
        ]
        candidate_scores[cat] = round(max(scores), 4)

    sorted_scores = dict(
        sorted(candidate_scores.items(), key=lambda x: x[1], reverse=True)
    )

    category = next(iter(sorted_scores))
    best_score = sorted_scores[category]

    state["messages"].append({
        "agent": "classifier",
        "note": f"Category selected via vector similarity: {category} (score={best_score})",
        "incident_summary_used": incident_text_for_embedding,
        "candidate_scores": sorted_scores
    })

    # ACTUAL LLM REASONING (CORE)
    # Classifier explains the vector-selected category using feedback from Decision Agent
    if feedback_msgs:
        prompt = f"""
        You are a petty crime reasoning agent for Singapore.

        Text:
        {state["raw_text"]}

        Final category selected by vector similarity:
        {category}

        Feedback:
        {feedback_msgs}

        Explain why this category fits the text, or explain what evidence is weak.

        Respond ONLY in JSON:
        {{
            "llm_reasoning": "..."
        }}
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        raw = response.choices[0].message.content
        raw = raw.replace("```json", "").replace("```", "").strip()

        try:
            result = json.loads(raw)

            if "llm_reasoning" not in result:
                raise ValueError

        except (json.JSONDecodeError, ValueError):
            result = {
                "llm_reasoning": "LLM output invalid, fallback used"
            }

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

    Extracted Fields:
    location={location}
    time={time}
    action={action}

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
            "note": "LLM feature extraction failed, fallback used",
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
        0.5 * features.get("specific_location", 0) +
        0.5 * features.get("specific_time", 0) +
        0.5 * features.get("specific_action", 0) +
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
        0.05 * risk
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
        "incident_summary": incident_summary,
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
# =========================================================
def decision_node(state: State) -> dict:

    # HARD RETRY GUARD
    # Force reject if retry limit is reached and authenticity is still low
    if (
        state["retry_count"] >= 2
    ):
        state["decision"] = "reject"

        state["messages"].append({
            "agent": "decision",
            "note": "Decision: reject",
            "decision_reason": "Retry limit reached with low authenticity score"
        })

        return state

    prompt = f"""
    You are the final decision agent in a petty crime incident pipeline for Singapore.

    Decide one of:
    - publish
    - needs_retry
    - reject

    Incident data:
    category: {state["category"]}
    authenticity_score: {state["authenticity_score"]}
    severity: {state["severity"]}
    location: {state["location"]}
    time: {state["time"]}
    action: {state["action"]}
    retry_count: {state["retry_count"]}

    Authenticity Score interpretation:
    - 0.00 to 0.09 = weak evidence
    - 0.10 to 0.15 = moderate evidence
    - 0.16 to 0.25 = strong evidence
    - 0.25 and above = very strong
    - Do not treat 0.25 as low.
    - In this system, a score of 0.25 can already support publication if the report contains a concrete location, time, and action.
    - Community reports do not require police reports, media, or multiple witnesses to be publishable.

    Rules:
    - Reports with concrete location, time, and action should generally be publishable even without witness statements, media, or police reports.
    - Do not require corroborating evidence for ordinary community petty-crime reports if the incident details are specific and coherent.
    - Use "needs_retry" only if missing information could realistically be improved.
    - Prefer "publish" over repeated retries when location, time, and action are already concrete.

    Respond ONLY in JSON:
    {{
        "decision": "publish | needs_retry | reject",
        "decision_reason": "...",
        "instruction": "..."
    }}
    """

    response = client.chat.completions.create(
        model="gpt-5-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.choices[0].message.content
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        result = json.loads(raw)

        if "decision" not in result:
            raise ValueError

    except (json.JSONDecodeError, ValueError):
        if state["retry_count"] >= 2:
            result = {
                "decision": "reject",
                "decision_reason": "LLM output invalid, fallback reject used",
                "instruction": "No further retry"
            }
        else:
            result = {
                "decision": "needs_retry",
                "decision_reason": "LLM output invalid, fallback retry used",
                "instruction": "Improve classification using stronger evidence"
            }

    state["decision"] = result["decision"]

    if state["decision"] == "needs_retry":
        state["retry_count"] += 1

        state["messages"].append({
            "agent": "decision",
            "feedback_to": "classifier",
            "instruction": result.get("instruction", "Improve classification using stronger evidence"),
            "reason": result.get("decision_reason", "Needs stronger evidence")
        })

    state["messages"].append({
        "agent": "decision",
        "note": f"Decision: {state['decision']}",
        "decision_reason": result.get("decision_reason", "No reason provided")
    })

    print("DEBUG retry_count:", state["retry_count"])
    print("DEBUG current decision state:", state.get("decision"))

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
        "incident_summary": None,

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
        # print("\n=== RAW MESSAGES ===\n")
        # print(result["messages"])

        if result["decision"] == "publish":
            accepted += 1
        elif result["decision"] == "reject":
            rejected += 1

        print(f"Incident ID: {result['incident_id']}")
        print(f"Retry Count: {result['retry_count']}")
        print(f"Decision: {result['decision'].upper()}")

        for msg in reversed(result["messages"]):
            if msg.get("agent") == "decision" and "decision_reason" in msg:
                print(f"Decision Reason: {msg['decision_reason']}")
                break

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

def print_agent_conversation(result: dict):
    print("\nAgent Conversation:\n")

    for msg in result.get("messages", []):
        agent = msg.get("agent", "unknown")

        if "llm_reasoning" in msg:
            print(f"  {agent.capitalize()} (LLM):")
            print(f"   {msg['llm_reasoning']}\n")

        elif "reasoning" in msg:
            print(f"  {agent.capitalize()} (system):")
            print(f"   {msg['reasoning']}\n")

        elif "instruction" in msg:
            print(f"  {agent.capitalize()}:")
            print(f"   {msg['instruction']}\n")

        elif "decision_reason" in msg:
            print(f"  {agent.capitalize()} decision reason:")
            print(f"   {msg['decision_reason']}\n")

        elif "note" in msg:
            print(f"  {agent.capitalize()}:")
            print(f"   {msg['note']}\n")

    print("-" * 40)