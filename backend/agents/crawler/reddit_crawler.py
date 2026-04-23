from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any

import requests
from dotenv import load_dotenv
from transformers import pipeline

DEFAULT_SUBREDDIT = "singapore"
DEFAULT_INCREMENTAL_LIMIT = 25
DEFAULT_BACKFILL_LIMIT = 100
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) OSINT-Hackathon-Bot/1.0"
)
DEFAULT_TIMEOUT = 15
REDDIT_BASE_URL = "https://www.reddit.com"
RELEVANT_LABEL = "petty crime, theft, or scam"
OTHER_LABEL = "general news or casual conversation"
RELEVANCE_THRESHOLD = 0.60

classifier = pipeline(
    "zero-shot-classification",
    model="facebook/bart-large-mnli",
)


def get_supabase_client():
    try:
        from supabase import create_client
    except ImportError as exc:
        raise RuntimeError(
            "Supabase SDK is not installed. Install it with `pip install supabase`."
        ) from exc

    load_dotenv()
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        raise RuntimeError(
            "Missing Supabase credentials. Set SUPABASE_URL and SUPABASE_KEY."
        )

    return create_client(supabase_url, supabase_key)


def get_latest_reddit_id(supabase: Any) -> str | None:
    """Return the most recent stored Reddit source_item_id checkpoint."""
    response = (
        supabase.table("incidents")
        .select("source_item_id")
        .eq("source_platform", "reddit")
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )

    for row in response.data or []:
        source_item_id = str(row.get("source_item_id") or "").strip()
        if source_item_id:
            return source_item_id
    return None


def fetch_new_posts(
    subreddit_name: str,
    limit: int,
    user_agent: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> list[dict[str, Any]]:
    """Fetch the newest posts from a subreddit using Reddit's public JSON endpoint."""
    url = f"{REDDIT_BASE_URL}/r/{subreddit_name}/new.json"
    headers = {"User-Agent": user_agent}
    params = {"limit": limit}

    response = requests.get(url, headers=headers, params=params, timeout=timeout)
    if response.status_code == 429:
        raise RuntimeError(
            "Reddit returned HTTP 429 (Too Many Requests). "
            "Use a clear custom User-Agent and reduce request frequency."
        )
    response.raise_for_status()

    payload = response.json()
    children = payload.get("data", {}).get("children", [])

    posts: list[dict[str, Any]] = []
    for child in children:
        if isinstance(child, dict):
            post_data = child.get("data", {})
            if isinstance(post_data, dict):
                posts.append(post_data)

    return posts


def extract_submission_fields(post_data: dict[str, Any]) -> dict[str, str]:
    post_id = str(post_data.get("id") or "").strip()
    title = str(post_data.get("title") or "").strip()
    body_text = str(post_data.get("selftext") or "").strip()
    permalink = str(post_data.get("permalink") or "").strip()
    post_url = (
        f"{REDDIT_BASE_URL}{permalink}"
        if permalink.startswith("/")
        else str(post_data.get("url") or "").strip()
    )

    created_utc = post_data.get("created_utc")
    timestamp = ""
    if created_utc is not None:
        timestamp = datetime.fromtimestamp(float(created_utc), tz=timezone.utc).isoformat()

    return {
        "post_id": post_id,
        "title": title,
        "body_text": body_text,
        "post_url": post_url,
        "timestamp": timestamp,
    }


def evaluate_post_relevance(title: str, body_text: str) -> bool:
    content = f"{title}\n\n{body_text}".strip()
    if not content:
        return False

    result = classifier(
        content,
        candidate_labels=[RELEVANT_LABEL, OTHER_LABEL],
        multi_label=False,
    )
    labels = result.get("labels", [])
    scores = result.get("scores", [])
    if not labels or not scores:
        return False

    top_label = str(labels[0])
    top_score = float(scores[0])
    return top_label == RELEVANT_LABEL and top_score > RELEVANCE_THRESHOLD


def to_incident_payload(extracted: dict[str, str]) -> dict[str, Any]:
    post_id = extracted["post_id"]
    title = extracted["title"]
    body_text = extracted["body_text"]
    raw_text = f"{title}\n\n{body_text}".strip()
    dedupe_key = f"reddit_{post_id}" if post_id else "reddit_unknown"

    return {
        "source_platform": "reddit",
        "source_type": "post",
        "source_item_id": post_id or None,
        "source_url": extracted["post_url"],
        "raw_text": raw_text,
        "timestamp_text": extracted["timestamp"] or None,
        "normalized_time": extracted["timestamp"] or None,
        "dedupe_key": dedupe_key,
        "workflow_stage": "crawl",
        "status": "queued",
    }


def upload_to_supabase(payloads: list[dict], supabase: Any | None = None) -> int:
    """Upsert incident payloads into Supabase using dedupe_key conflict handling."""
    if not payloads:
        return 0

    client = supabase or get_supabase_client()
    inserted = 0

    for payload in payloads:
        client.table("incidents").upsert(
            payload,
            on_conflict="dedupe_key",
            ignore_duplicates=True,
        ).execute()
        inserted += 1

    return inserted


def crawl_reddit_posts(
    subreddit_name: str = DEFAULT_SUBREDDIT,
    limit: int = DEFAULT_INCREMENTAL_LIMIT,
    user_agent: str = DEFAULT_USER_AGENT,
    latest_reddit_id: str | None = None,
    backfill: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    posts = fetch_new_posts(
        subreddit_name=subreddit_name,
        limit=limit,
        user_agent=user_agent,
    )
    payloads: list[dict[str, Any]] = []
    scanned = 0
    passed_filter = 0
    stopped_at_checkpoint = False

    for post_data in posts:
        extracted = extract_submission_fields(post_data)
        scanned += 1
        if (
            not backfill
            and latest_reddit_id
            and extracted["post_id"]
            and extracted["post_id"] == latest_reddit_id
        ):
            stopped_at_checkpoint = True
            break

        if evaluate_post_relevance(extracted["title"], extracted["body_text"]):
            payloads.append(to_incident_payload(extracted))
            passed_filter += 1

    stats = {
        "fetched": len(posts),
        "scanned": scanned,
        "stopped_at_checkpoint": stopped_at_checkpoint,
        "passed_filter": passed_filter,
    }
    return payloads, stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Scrape matching posts from r/singapore and output JSON payloads "
            "for the OSINT pipeline."
        )
    )
    parser.add_argument(
        "--subreddit",
        default=DEFAULT_SUBREDDIT,
        help=f"Subreddit to crawl (default: {DEFAULT_SUBREDDIT})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "Optional override for incremental mode only. "
            f"Default incremental={DEFAULT_INCREMENTAL_LIMIT}. Ignored with --backfill."
        ),
    )
    parser.add_argument(
        "--user-agent",
        default=DEFAULT_USER_AGENT,
        help=(
            "User-Agent header sent to Reddit. "
            "A custom value is required to avoid 429 errors."
        ),
    )
    parser.add_argument(
        "--backfill",
        action="store_true",
        help=(
            "Run backfill mode: ignore checkpoint and process "
            f"up to {DEFAULT_BACKFILL_LIMIT} newest posts."
        ),
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Upsert filtered payloads into Supabase incidents table.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Print formatted JSON for readability.",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help=(
            "Print crawler diagnostics to stderr "
            "(fetched, scanned, stopped_at_checkpoint, passed_filter)."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    effective_limit = (
        DEFAULT_BACKFILL_LIMIT
        if args.backfill
        else (args.limit if args.limit is not None else DEFAULT_INCREMENTAL_LIMIT)
    )

    supabase = None
    latest_reddit_id = None
    if not args.backfill:
        supabase = get_supabase_client()
        latest_reddit_id = get_latest_reddit_id(supabase)

    payloads, stats = crawl_reddit_posts(
        subreddit_name=args.subreddit,
        limit=effective_limit,
        user_agent=args.user_agent,
        latest_reddit_id=latest_reddit_id,
        backfill=args.backfill,
    )
    if args.upload:
        upload_to_supabase(payloads, supabase=supabase)

    if args.stats:
        print(
            json.dumps(stats, ensure_ascii=False),
            file=sys.stderr,
        )

    print(
        json.dumps(
            payloads,
            indent=2 if args.pretty else None,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
