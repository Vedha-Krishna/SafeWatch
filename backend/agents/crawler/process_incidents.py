import json
import os
from typing import Any, Optional, Optional, Optional, Optional, Optional, Optional, Optional, Optional, Optional

from dotenv import load_dotenv
from supabase import create_client

try:
    from .orchestration12 import run_pipeline_for_1_post
except ImportError:
    try:
        from backend.agents.crawler.orchestration12 import run_pipeline_for_1_post
    except ImportError:
        try:
            from agents.crawler.orchestration12 import run_pipeline_for_1_post
        except ImportError:
            from orchestration12 import run_pipeline_for_1_post


load_dotenv()


AGENT_ROLE_ALIASES = {
    "crawler": "crawler",
    "cleaner": "cleaner",
    "classifier": "classifier",
    "decision": "decision_agent",
    "decision_agent": "decision_agent",
}


def normalize_agent_role(value: Any) -> str:
    role = str(value or "").strip().lower().replace(" ", "_")
    if role in AGENT_ROLE_ALIASES:
        return AGENT_ROLE_ALIASES[role]
    raise ValueError(f"Invalid agent role for incident_agent_messages.agent: {value!r}")


def get_supabase_client() -> Any:
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY in environment variables.")

    return create_client(supabase_url, supabase_key)


def fetch_queued_incidents(supabase: Any, limit: Optional[int] = None) -> list[dict]:
    # Read cleaned rows, including partial retries where a previous failed run
    # wrote analysis/decision fields but did not advance the queue status.
    query = (
        supabase.table("incident_full")
        .select("*")
        .eq("status", "cleaned")
        .not_.is_("cleaned_content", "null")
        .order("created_at", desc=False)
    )

    if limit is not None and limit > 0:
        query = query.limit(limit)

    response = query.execute()
    return response.data or []


def db_row_to_pipeline_input(row: dict) -> dict:
    return {
        "incident_id":    row["incident_id"],
        "source_platform": row["source_platform"],
        "source_url":     row["source_url"],
        "raw_text":       row["raw_text"],
        "cleaned_content": row.get("cleaned_content"),
        "topic_bucket":   row.get("topic_bucket"),
        "location_text":  row.get("location_text"),
        "normalized_time": row.get("normalized_time"),
    }


def update_incident_after_pipeline(supabase: Any, incident_id: str, result: dict) -> None:
    location_text   = result.get("location_text") or result.get("location")
    normalized_time = result.get("normalized_time") or result.get("timestamp_text")

    # Write classifier output to incident_analysis
    supabase.table("incident_analysis").upsert({
        "incident_id":       incident_id,
        "category":          result["category"],
        "category_score":    result.get("category_score"),
        "authenticity_score": result["authenticity_score"],
        "severity":          result["severity"],
    }).execute()

    # Write location to incident_locations (only if present)
    if location_text:
        supabase.table("incident_locations").upsert({
            "incident_id":  incident_id,
            "location_text": location_text,
        }).execute()

    # Write decision to incident_decisions
    supabase.table("incident_decisions").upsert({
        "incident_id": incident_id,
        "decision":    result["decision"],
    }).execute()

    # Write agent messages to incident_agent_messages (one row per message)
    messages = result.get("messages") or []
    for seq, msg in enumerate(messages):
        supabase.table("incident_agent_messages").insert({
            "incident_id":    incident_id,
            "agent":          normalize_agent_role(msg.get("agent")),
            "sequence_order": seq,
            "message_type":   msg.get("type", "note"),
            "summary":        msg.get("note") or msg.get("content") or "",
            "reasoning":      msg.get("reasoning") or msg.get("llm_reasoning"),
            "decision_reason": msg.get("decision_reason"),
            "metadata":       {k: v for k, v in msg.items()
                               if k not in {"agent", "type", "note", "content",
                                            "reasoning", "llm_reasoning", "decision_reason"}},
        }).execute()

    # Update normalized_time on the core incidents row if available
    if normalized_time:
        supabase.table("incidents").update(
            {"normalized_time": normalized_time, "timestamp_text": normalized_time}
        ).eq("incident_id", incident_id).execute()

    # Advance queue status to processed
    supabase.table("incident_queue").update(
        {"status": "processed"}
    ).eq("incident_id", incident_id).execute()


def process_queued_incidents(max_incidents: Optional[int] = None) -> dict[str, int]:
    if max_incidents is not None and max_incidents <= 0:
        print("Skipping incident processing because max_incidents is 0.")
        return {"found": 0, "processed": 0, "failed": 0}

    supabase = get_supabase_client()
    rows = fetch_queued_incidents(supabase, limit=max_incidents)
    stats = {"found": len(rows), "processed": 0, "failed": 0}

    print(f"Found {len(rows)} queued incidents.")

    for row in rows:
        try:
            post = db_row_to_pipeline_input(row)
            result = run_pipeline_for_1_post(post)

            print("\nAgent Conversation:\n")

            for msg in result["messages"]:
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

                elif "note" in msg:
                    print(f"  {agent.capitalize()}:")
                    print(f"   {msg['note']}\n")

            print("-" * 40)

            update_incident_after_pipeline(supabase, row["incident_id"], result)

            print(
                f"Processed incident id={row['incident_id']} | "
                f"decision={result['decision']} | "
                f"category={result['category']}"
            )
            stats["processed"] += 1

        except Exception as exc:
            print(f"Failed to process incident id={row.get('incident_id')}: {exc}")
            stats["failed"] += 1

    return stats


if __name__ == "__main__":
    print(process_queued_incidents())
