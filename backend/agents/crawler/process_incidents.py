import json
import os
from typing import Any

from dotenv import load_dotenv
from supabase import create_client

# import pipeline function from orchestration
from orchestration7 import run_pipeline_for_1_post


load_dotenv()


def get_supabase_client() -> Any:
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY in environment variables.")

    return create_client(supabase_url, supabase_key)


def fetch_queued_incidents(supabase: Any) -> list[dict]:
    response = (
        supabase.table("incidents")
        .select("*")
        .eq("status", "queued")
        .execute()
    )
    return response.data or []


def db_row_to_pipeline_input(row: dict) -> dict:
    return {
        "incident_id": row["incident_id"],  # use DB row id as stable identifier
        "source_platform": row["source_platform"],
        "source_url": row["source_url"],
        "raw_text": row["raw_text"],
    }


def update_incident_after_pipeline(supabase: Any, row_id: int, result: dict) -> None:
    update_payload = {
        "category": result["category"],
        "authenticity_score": result["authenticity_score"],
        "severity": result["severity"],
        "location_text": result["location"],
        "timestamp_text": result["time"],
        "action_text": result["action"],
        "decision": result["decision"],
        "agent_messages": json.dumps(result["messages"], ensure_ascii=False),
        "status": "processed",
    }

    (
        supabase.table("incidents")
        .update(update_payload)
        .eq("id", row_id)
        .execute()
    )


def process_queued_incidents() -> None:
    supabase = get_supabase_client()
    rows = fetch_queued_incidents(supabase)

    print(f"Found {len(rows)} queued incidents.")

    for row in rows:
        try:
            post = db_row_to_pipeline_input(row)
            result = run_pipeline_for_1_post(post)
            update_incident_after_pipeline(supabase, row["id"], result)

            print(
                f"Processed incident id={row['id']} | "
                f"decision={result['decision']} | "
                f"category={result['category']}"
            )

        except Exception as exc:
            print(f"Failed to process incident id={row.get('id')}: {exc}")


if __name__ == "__main__":
    process_queued_incidents()