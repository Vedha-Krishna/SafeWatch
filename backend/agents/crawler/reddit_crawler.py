from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from datetime import datetime, timezone
from typing import Any

import requests
from dotenv import load_dotenv
from transformers import pipeline

DEFAULT_SUBREDDIT = "mockpostsforNBT"
DEFAULT_INCREMENTAL_LIMIT = 25
DEFAULT_BACKFILL_LIMIT = 100
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) OSINT-Hackathon-Bot/1.0"
)
DEFAULT_TIMEOUT = 15
REDDIT_BASE_URL = "https://www.reddit.com"
RELEVANT_LABEL = "petty crime, theft, or scam"
OTHER_LABEL = "general news or casual conversation"
RELEVANCE_THRESHOLD = 0.25
DEFAULT_COMMENT_LIMIT = 10
MAX_CLASSIFY_CHARS = 4000
DEFAULT_MAX_RETRIES = 5
DEFAULT_REQUEST_DELAY = 0.35
DEFAULT_BACKOFF_BASE_SECONDS = 1.5

_classifier: Any | None = None


def get_classifier() -> Any:
    global _classifier

    if _classifier is None:
        _classifier = pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli",
        )

    return _classifier


def get_supabase_client():
    try:
        from supabase import create_client
    except ImportError as exc:
        raise RuntimeError(
            "Supabase SDK is not installed. Install it with `pip install supabase`."
        ) from exc

    load_dotenv()
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

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
    max_retries: int = DEFAULT_MAX_RETRIES,
    request_delay: float = DEFAULT_REQUEST_DELAY,
) -> list[dict[str, Any]]:
    """Fetch the newest posts from a subreddit using Reddit's public JSON endpoint."""
    url = f"{REDDIT_BASE_URL}/r/{subreddit_name}/new.json"
    headers = {"User-Agent": user_agent}
    params = {"limit": limit}

    payload = reddit_get_json(
        url=url,
        headers=headers,
        params=params,
        timeout=timeout,
        max_retries=max_retries,
        request_delay=request_delay,
    )
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
        "permalink": permalink,
        "post_url": post_url,
        "timestamp": timestamp,
    }


def truncate_for_classification(content: str, max_chars: int = MAX_CLASSIFY_CHARS) -> str:
    content = content.strip()
    if len(content) <= max_chars:
        return content
    return content[:max_chars].rsplit(" ", 1)[0].strip()


def classify_relevance(content: str) -> tuple[str, float]:
    if not content:
        return "", 0.0

    result = get_classifier()(
        truncate_for_classification(content),
        candidate_labels=[RELEVANT_LABEL, OTHER_LABEL],
        multi_label=False,
    )
    labels = result.get("labels", [])
    scores = result.get("scores", [])
    if not labels or not scores:
        return "", 0.0

    top_label = str(labels[0])
    top_score = float(scores[0])
    return top_label, top_score


def collect_comment_bodies(
    children: list[dict[str, Any]],
    bucket: list[str],
    max_items: int,
) -> None:
    if len(bucket) >= max_items:
        return
    for child in children:
        if len(bucket) >= max_items:
            return
        if not isinstance(child, dict):
            continue
        kind = child.get("kind")
        data = child.get("data", {})
        if kind != "t1" or not isinstance(data, dict):
            continue

        body = str(data.get("body") or "").strip()
        if body and body not in {"[deleted]", "[removed]"}:
            bucket.append(body)

        replies = data.get("replies")
        if isinstance(replies, dict):
            reply_children = replies.get("data", {}).get("children", [])
            if isinstance(reply_children, list):
                collect_comment_bodies(reply_children, bucket, max_items)


def fetch_post_comments(
    permalink: str,
    user_agent: str,
    comment_limit: int,
    timeout: int = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    request_delay: float = DEFAULT_REQUEST_DELAY,
) -> list[str]:
    if not permalink:
        return []
    comments_url = (
        f"{REDDIT_BASE_URL}{permalink}.json"
        if permalink.startswith("/")
        else f"{REDDIT_BASE_URL}{permalink}"
    )
    headers = {"User-Agent": user_agent}
    params = {"limit": max(1, comment_limit), "depth": 2, "sort": "new"}

    payload = reddit_get_json(
        url=comments_url,
        headers=headers,
        params=params,
        timeout=timeout,
        max_retries=max_retries,
        request_delay=request_delay,
    )
    if not isinstance(payload, list) or len(payload) < 2:
        return []
    comments_listing = payload[1]
    if not isinstance(comments_listing, dict):
        return []
    children = comments_listing.get("data", {}).get("children", [])
    if not isinstance(children, list):
        return []

    comments: list[str] = []
    collect_comment_bodies(children, comments, max_items=max(1, comment_limit))
    return comments


def evaluate_post_relevance(
    title: str,
    body_text: str,
    comment_texts: list[str] | None = None,
) -> tuple[bool, str]:
    post_content = f"{title}\n\n{body_text}".strip()
    top_label, top_score = classify_relevance(post_content)
    if top_label == RELEVANT_LABEL and top_score > RELEVANCE_THRESHOLD:
        return True, "post"

    if comment_texts:
        comment_blob = "\n".join(comment_texts).strip()
        enriched_content = f"{post_content}\n\nComments:\n{comment_blob}".strip()
        top_label, top_score = classify_relevance(enriched_content)
        if top_label == RELEVANT_LABEL and top_score > RELEVANCE_THRESHOLD:
            return True, "comments"

    return False, ""


def parse_retry_after_seconds(raw_retry_after: str | None) -> float | None:
    if raw_retry_after is None:
        return None
    try:
        retry_after = float(raw_retry_after)
    except (TypeError, ValueError):
        return None
    if retry_after < 0:
        return None
    return retry_after


def compute_backoff_seconds(attempt: int, retry_after: str | None = None) -> float:
    parsed_retry_after = parse_retry_after_seconds(retry_after)
    if parsed_retry_after is not None:
        return max(parsed_retry_after, 0.5)

    base = DEFAULT_BACKOFF_BASE_SECONDS * (2**attempt)
    jitter = random.uniform(0.0, 0.75)
    return max(base + jitter, 0.5)


def reddit_get_json(
    url: str,
    headers: dict[str, str],
    params: dict[str, Any],
    timeout: int = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    request_delay: float = DEFAULT_REQUEST_DELAY,
) -> Any:
    retries = max(0, max_retries)
    last_error: Exception | None = None

    for attempt in range(retries + 1):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=timeout)
        except requests.RequestException as exc:
            last_error = exc
            if attempt >= retries:
                break
            wait_seconds = compute_backoff_seconds(attempt)
            print(
                f"Reddit request failed ({exc.__class__.__name__}). "
                f"Retrying in {wait_seconds:.2f}s (attempt {attempt + 1}/{retries}).",
                file=sys.stderr,
            )
            time.sleep(wait_seconds)
            continue

        if response.status_code == 429:
            if attempt >= retries:
                raise RuntimeError(
                    "Reddit returned HTTP 429 (Too Many Requests). "
                    "Use a unique User-Agent and reduce request frequency."
                )
            wait_seconds = compute_backoff_seconds(
                attempt=attempt,
                retry_after=response.headers.get("Retry-After"),
            )
            print(
                f"Reddit rate-limited request (429). "
                f"Retrying in {wait_seconds:.2f}s (attempt {attempt + 1}/{retries}).",
                file=sys.stderr,
            )
            time.sleep(wait_seconds)
            continue

        if response.status_code >= 500:
            if attempt >= retries:
                response.raise_for_status()
            wait_seconds = compute_backoff_seconds(attempt)
            print(
                f"Reddit server error {response.status_code}. "
                f"Retrying in {wait_seconds:.2f}s (attempt {attempt + 1}/{retries}).",
                file=sys.stderr,
            )
            time.sleep(wait_seconds)
            continue

        response.raise_for_status()
        if request_delay > 0:
            time.sleep(request_delay)
        return response.json()

    if last_error is not None:
        raise RuntimeError(f"Reddit request failed after retries: {last_error}") from last_error
    raise RuntimeError("Reddit request failed after retries.")


def to_incident_payload(
    extracted: dict[str, str],
    comment_texts: list[str] | None = None,
) -> dict[str, Any]:
    post_id = extracted["post_id"]
    title = extracted["title"]
    body_text = extracted["body_text"]
    raw_parts = [title, body_text]
    if comment_texts:
        comments_block = "\n".join(f"- {comment}" for comment in comment_texts if comment)
        if comments_block:
            raw_parts.append(f"Comments:\n{comments_block}")
    raw_text = "\n\n".join(part for part in raw_parts if part).strip()
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
        "status": "queued",
    }


def upload_to_supabase(payloads: list[dict], supabase: Any | None = None) -> int:
    """Upsert incident payloads into Supabase using dedupe_key conflict handling.

    Splits each payload across the normalised tables:
      - core fields  → incidents      (conflict on dedupe_key)
      - status field → incident_queue (conflict on incident_id, skip if already queued)
    """
    if not payloads:
        return 0

    client = supabase or get_supabase_client()
    inserted = 0

    # Columns that belong to incident_queue, not incidents
    _QUEUE_COLS = {"status", "locked_by", "locked_at", "retry_count", "last_error",
                   "current_agent", "next_agent", "available_at", "max_attempts"}

    for payload in payloads:
        queue_fields = {k: v for k, v in payload.items() if k in _QUEUE_COLS}
        incident_fields = {k: v for k, v in payload.items() if k not in _QUEUE_COLS}

        # Upsert the core incident row (do nothing on duplicate dedupe_key)
        client.table("incidents").upsert(
            incident_fields,
            on_conflict="dedupe_key",
            ignore_duplicates=True,
        ).execute()

        # Re-fetch the incident_id by dedupe_key — ignore_duplicates upsert
        # does not return data even when a row is inserted (PostgREST limitation)
        lookup = (
            client.table("incidents")
            .select("incident_id")
            .eq("dedupe_key", incident_fields["dedupe_key"])
            .maybe_single()
            .execute()
        )
        if not lookup.data:
            print(f"Warning: could not find incident after upsert for dedupe_key={incident_fields.get('dedupe_key')}")
            continue

        incident_id = lookup.data["incident_id"]
        queue_fields.setdefault("status", "queued")
        queue_fields["incident_id"] = incident_id
        client.table("incident_queue").upsert(
            queue_fields,
            on_conflict="incident_id",
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
    include_comments: bool = False,
    comment_limit: int = DEFAULT_COMMENT_LIMIT,
    request_delay: float = DEFAULT_REQUEST_DELAY,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    posts = fetch_new_posts(
        subreddit_name=subreddit_name,
        limit=limit,
        user_agent=user_agent,
        request_delay=request_delay,
        max_retries=max_retries,
    )
    payloads: list[dict[str, Any]] = []
    scanned = 0
    passed_filter = 0
    stopped_at_checkpoint = False
    comment_posts_checked = 0
    comment_items_used = 0
    relevant_from_comments = 0

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

        comment_texts: list[str] = []

        if include_comments:
            comment_texts = fetch_post_comments(
                permalink=extracted["permalink"],
                user_agent=user_agent,
                comment_limit=comment_limit,
                request_delay=request_delay,
                max_retries=max_retries,
            )
            comment_posts_checked += 1
            comment_items_used += len(comment_texts)

        payloads.append(
            to_incident_payload(
                extracted,
                comment_texts=comment_texts if include_comments else None,
            )
        )

    passed_filter += 1

    stats = {
        "fetched": len(posts),
        "scanned": scanned,
        "stopped_at_checkpoint": stopped_at_checkpoint,
        "passed_filter": passed_filter,
        "comment_posts_checked": comment_posts_checked,
        "comment_items_used": comment_items_used,
        "relevant_from_comments": relevant_from_comments,
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
            "("
            "fetched, scanned, stopped_at_checkpoint, passed_filter, "
            "comment_posts_checked, comment_items_used, relevant_from_comments"
            ")."
        ),
    )
    parser.add_argument(
        "--include-comments",
        action="store_true",
        help=(
            "Fetch and analyze comments for posts that fail initial relevance "
            "classification."
        ),
    )
    parser.add_argument(
        "--comment-limit",
        type=int,
        default=DEFAULT_COMMENT_LIMIT,
        help=(
            "Max number of comment bodies to consider per post when "
            f"--include-comments is enabled (default: {DEFAULT_COMMENT_LIMIT})."
        ),
    )
    parser.add_argument(
        "--request-delay",
        type=float,
        default=DEFAULT_REQUEST_DELAY,
        help=(
            "Delay in seconds after each successful Reddit request. "
            f"Increase this if you hit 429 (default: {DEFAULT_REQUEST_DELAY})."
        ),
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=DEFAULT_MAX_RETRIES,
        help=(
            "Max retry attempts for Reddit HTTP 429/network/server errors "
            f"(default: {DEFAULT_MAX_RETRIES})."
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
        include_comments=args.include_comments,
        comment_limit=max(1, args.comment_limit),
        request_delay=max(0.0, args.request_delay),
        max_retries=max(0, args.max_retries),
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
