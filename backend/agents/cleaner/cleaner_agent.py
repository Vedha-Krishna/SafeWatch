from __future__ import annotations

import os
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal, Optional
from zoneinfo import ZoneInfo

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

    action_text: Optional[str] = Field(
        default=None,
        description=(
            "Short factual action/event phrase for dashboard display, "
            "e.g. 'wallet stolen', 'phone snatched', 'suspected scam', 'shop break-in'."
        ),
    )

    topic_bucket: Literal["singapore_news", "singapore_viral", "other"]
    location_text: Optional[str] = Field(
        default=None,
        description="Normalized Singapore location name, e.g. 'Ang Mo Kio MRT'.",
    )
    latitude: Optional[float] = Field(
        default=None,
        description="Approximate latitude in Singapore (expected range 1.1 to 1.5).",
    )
    longitude: Optional[float] = Field(
        default=None,
        description="Approximate longitude in Singapore (expected range 103.6 to 104.1).",
    )
    normalized_time: Optional[str] = Field(
        default=None,
        description="ISO-8601 timestamp in SGT (UTC+8), e.g. 2026-04-23T20:00:00+08:00.",
    )


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
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
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
    Selection rule: status='queued' AND cleaned_content is null.
    Lock rule: set status='in_progress' and locked_by='cleaner_agent'.
    """
    now_iso = datetime.now(ZoneInfo("UTC")).isoformat()
    response = (
        supabase.table("incidents")
        .select("incident_id, raw_text, status, cleaned_content, source_platform, normalized_time")
        .eq("status", "queued")
        .is_("cleaned_content", "null")
        .is_("locked_by", "null")
        # .lte("available_at", now_iso)
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
            "locked_by": "cleaner_agent",
            "locked_at": now_iso,
        }
        lock_response = (
            supabase.table("incidents")
            .update(lock_payload)
            .eq("incident_id", incident_id)
            .eq("status", "queued")
            .is_("cleaned_content", "null")
            .is_("locked_by", "null")
            .execute()
        )

        if lock_response.data:
            return incident

    return None


def choose_normalized_time(
    source_platform: str | None,
    existing_normalized_time: Any,
    cleaned_normalized_time: str | None,
) -> str | None:
    existing_time = str(existing_normalized_time or "").strip() or None
    cleaned_time = str(cleaned_normalized_time or "").strip() or None
    source = str(source_platform or "").strip().lower()

    # Preserve crawler-provided Reddit post timestamps so later LLM steps
    # don't overwrite source creation time with an inferred "current" time.
    if source == "reddit" and existing_time:
        return existing_time
    return cleaned_time or existing_time


def clean_with_llm(openai_client: Any, raw_text: str) -> CleanedIncident:
    current_sgt = datetime.now(ZoneInfo("Asia/Singapore")).isoformat(timespec="seconds")
    system_prompt = (
        "You are the Cleaner Agent for a Singapore OSINT incident pipeline. "
        "Rewrite noisy user text into a formal, objective incident summary.\n"
        f"Current Singapore time (SGT, UTC+8): {current_sgt}\n"
        "Rules:\n"
        "- Output exactly 1-2 sentences in cleaned_content.\n"
        "- Output action_text as a short factual event phrase, e.g. 'wallet stolen', 'suspected scam', 'shop break-in'.\n"
        "- Remove slang, emotion, exaggeration, and usernames/handles.\n"
        "- Keep factual details only (what happened, where, when, who/what affected if available).\n"
        "- Select topic_bucket as one of: singapore_news, singapore_viral, other.\n"
        "- Geocoder behavior:\n"
        "  - If a Singapore location is detected, output location_text as a normalized place name.\n"
        "  - Also output approximate coordinates in Singapore bounds only: latitude 1.1-1.5, longitude 103.6-104.1.\n"
        "  - If no reliable location, set location_text, latitude, longitude to null.\n"
        "- Time normalization behavior:\n"
        "  - Convert relative time phrases (e.g. yesterday, last night, ytd, this morning) "
        "to absolute ISO-8601 in SGT using the provided current SGT reference.\n"
        "  - If no reliable time is available, set normalized_time to null.\n"
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
    source_platform: str | None = None,
    existing_normalized_time: Any = None,
) -> None:
    normalized_time = choose_normalized_time(
        source_platform=source_platform,
        existing_normalized_time=existing_normalized_time,
        cleaned_normalized_time=cleaned_incident.normalized_time,
    )
    update_payload = {
        "cleaned_content": cleaned_incident.cleaned_content,
        "action_text": cleaned_incident.action_text,
        "topic_bucket": cleaned_incident.topic_bucket,
        "location_text": cleaned_incident.location_text,
        "latitude": cleaned_incident.latitude,
        "longitude": cleaned_incident.longitude,
        "normalized_time": normalized_time,
        "status": "queued",
        "locked_by": None,
        "locked_at": None,
    }
    supabase.table("incidents").update(update_payload).eq("incident_id", incident_id).execute()


def mark_failed(supabase: Any, incident_id: Any, _error_message: str) -> None:
    supabase.table("incidents").update(
        {
            "status": "failed",
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
        update_and_handoff(
            supabase,
            incident_id,
            cleaned_incident,
            source_platform=str(incident.get("source_platform") or ""),
            existing_normalized_time=incident.get("normalized_time"),
        )
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
    processed = 0

    while run_once():
        processed += 1

    print(f"Cleaner finished. Processed {processed} incident(s).")
