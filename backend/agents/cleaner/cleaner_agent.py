from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from openai import OpenAI


class CleanedIncident(BaseModel):
    cleaned_content: str = Field(
        ...,
        description=(
            "Formal, objective 1-2 sentence summary of the petty crime/scam event, "
            "with slang, emotion, and usernames removed."
        ),
    )
    topic_bucket: Literal["singapore_news", "singapore_viral", "other"]


def get_supabase_client():
    """Create a Supabase client from environment variables."""
    try:
        from supabase import create_client
    except ImportError as exc:
        raise RuntimeError(
            "Supabase SDK is not installed. Install it with `pip install supabase`."
        ) from exc

    load_dotenv()
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = (
        os.getenv("SUPABASE_KEY")
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
    )

    if not supabase_url or not supabase_key:
        raise RuntimeError(
            "Missing Supabase credentials. Set SUPABASE_URL and SUPABASE_KEY "
            "(or SUPABASE_SERVICE_ROLE_KEY / SUPABASE_ANON_KEY)."
        )

    return create_client(supabase_url, supabase_key)


def get_openai_client() -> "OpenAI":
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "OpenAI SDK is not installed. Install it with `pip install openai`."
        ) from exc

    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY in environment.")
    return OpenAI(api_key=api_key)


def fetch_and_lock_incident(supabase: Any) -> dict[str, Any] | None:
    """
    Claim one incident for cleaning.
    Selection rule: status='queued' AND next_agent='cleaner'.
    Lock rule: set status='in_progress' and locked_by='cleaner_agent'.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    response = (
        supabase.table("incidents")
        .select("incident_id, raw_text, status, next_agent")
        .eq("status", "queued")
        .eq("next_agent", "cleaner")
        .is_("locked_by", "null")
        .lte("available_at", now_iso)
        .order("created_at", desc=False)
        .limit(25)
        .execute()
    )

    candidates = response.data or []
    if not candidates:
        return None

    for incident in candidates:
        incident_id = incident.get("incident_id")
        if not incident_id:
            continue

        lock_payload = {
            "status": "in_progress",
            "current_agent": "cleaner",
            "locked_by": "cleaner_agent",
            "locked_at": now_iso,
        }
        lock_response = (
            supabase.table("incidents")
            .update(lock_payload)
            .eq("incident_id", incident_id)
            .eq("status", "queued")
            .eq("next_agent", "cleaner")
            .is_("locked_by", "null")
            .execute()
        )

        if lock_response.data:
            return incident

    return None


def clean_with_llm(openai_client: Any, raw_text: str) -> CleanedIncident:
    system_prompt = (
        "You are the Cleaner Agent for a Singapore OSINT incident pipeline. "
        "Rewrite noisy user text into a formal, objective incident summary.\n"
        "Rules:\n"
        "- Output exactly 1-2 sentences in cleaned_content.\n"
        "- Remove slang, emotion, exaggeration, and usernames/handles.\n"
        "- Keep factual details only (what happened, where, when, who/what affected if available).\n"
        "- Select topic_bucket as one of: singapore_news, singapore_viral, other.\n"
        "- singapore_news: factual local incident/scam/crime/safety report in Singapore.\n"
        "- singapore_viral: socially viral discussion/drama content tied to Singapore.\n"
        "- other: unrelated, unclear, or insufficiently relevant content."
    )

    completion = openai_client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": raw_text},
        ],
        response_format=CleanedIncident,
        temperature=0,
    )

    message = completion.choices[0].message
    if message.parsed is None:
        refusal = getattr(message, "refusal", None)
        raise RuntimeError(f"Cleaner model did not return parsed output. Refusal: {refusal}")

    return message.parsed


def update_and_handoff(
    supabase: Any,
    incident_id: Any,
    cleaned_incident: CleanedIncident,
) -> None:
    update_payload = {
        "cleaned_content": cleaned_incident.cleaned_content,
        "topic_bucket": cleaned_incident.topic_bucket,
        "workflow_stage": "clean",
        "current_agent": "cleaner",
        "next_agent": "classifier",
        "status": "queued",
        "locked_by": None,
        "locked_at": None,
    }
    supabase.table("incidents").update(update_payload).eq("incident_id", incident_id).execute()


def mark_failed(supabase: Any, incident_id: Any, _error_message: str) -> None:
    supabase.table("incidents").update(
        {
            "status": "failed",
            "current_agent": "cleaner",
            "locked_by": None,
            "locked_at": None,
            "last_error": _error_message[:1000],
        }
    ).eq("incident_id", incident_id).execute()


def run_once() -> bool:
    supabase = get_supabase_client()
    openai_client = get_openai_client()

    incident = fetch_and_lock_incident(supabase)
    if not incident:
        print("No incident available for cleaner_agent.")
        return False

    incident_id = incident.get("incident_id")
    raw_text = str(incident.get("raw_text") or "").strip()

    if not raw_text:
        mark_failed(supabase, incident_id, "Incident has no raw_text.")
        print(f"Incident {incident_id} failed: missing raw text.")
        return False

    try:
        cleaned_incident = clean_with_llm(openai_client, raw_text)
        update_and_handoff(supabase, incident_id, cleaned_incident)
    except Exception as exc:
        mark_failed(supabase, incident_id, str(exc))
        print(f"Incident {incident_id} failed during cleaning: {exc}")
        return False

    print(
        f"Incident {incident_id} cleaned and handed off to classifier "
        f"(topic_bucket={cleaned_incident.topic_bucket})."
    )
    return True


if __name__ == "__main__":
    run_once()
