from __future__ import annotations

import os
from datetime import datetime, timezone
from time import perf_counter
from typing import Any


DEFAULT_MAX_CLEANER_RUNS = 5
DEFAULT_MAX_PROCESS_INCIDENTS = 5


def _int_env(name: str, default: int, minimum: int = 0) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        value = int(raw_value)
    except ValueError:
        return default

    return max(minimum, value)


def _float_env(name: str, default: float, minimum: float = 0.0) -> float:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        value = float(raw_value)
    except ValueError:
        return default

    return max(minimum, value)


def _bool_env(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def run_crawler_step() -> dict[str, Any]:
    try:
        from .agents.crawler import reddit_crawler
    except ImportError:
        from agents.crawler import reddit_crawler

    supabase = reddit_crawler.get_supabase_client()
    latest_reddit_id = reddit_crawler.get_latest_reddit_id(supabase)

    payloads, stats = reddit_crawler.crawl_reddit_posts(
        subreddit_name=os.getenv("REDDIT_SUBREDDIT", reddit_crawler.DEFAULT_SUBREDDIT),
        limit=_int_env(
            "CRON_CRAWLER_LIMIT",
            reddit_crawler.DEFAULT_INCREMENTAL_LIMIT,
            minimum=1,
        ),
        user_agent=os.getenv("REDDIT_USER_AGENT", reddit_crawler.DEFAULT_USER_AGENT),
        latest_reddit_id=latest_reddit_id,
        include_comments=_bool_env("CRON_INCLUDE_COMMENTS", default=False),
        comment_limit=_int_env(
            "CRON_COMMENT_LIMIT",
            reddit_crawler.DEFAULT_COMMENT_LIMIT,
            minimum=1,
        ),
        request_delay=_float_env(
            "CRON_REDDIT_REQUEST_DELAY",
            reddit_crawler.DEFAULT_REQUEST_DELAY,
        ),
        max_retries=_int_env(
            "CRON_REDDIT_MAX_RETRIES",
            reddit_crawler.DEFAULT_MAX_RETRIES,
        ),
    )

    upserted = reddit_crawler.upload_to_supabase(payloads, supabase=supabase)

    return {
        "latest_reddit_id": latest_reddit_id,
        "candidate_payloads": len(payloads),
        "upserted": upserted,
        "stats": stats,
    }


def run_cleaner_step() -> dict[str, int]:
    try:
        from .agents.cleaner import cleaner_agent
    except ImportError:
        from agents.cleaner import cleaner_agent

    max_runs = _int_env(
        "CRON_MAX_CLEANER_RUNS",
        DEFAULT_MAX_CLEANER_RUNS,
        minimum=0,
    )
    processed = 0

    for _ in range(max_runs):
        if not cleaner_agent.run_once():
            break
        processed += 1

    return {
        "max_runs": max_runs,
        "processed": processed,
    }


def run_process_incidents_step() -> dict[str, int]:
    try:
        from .agents.crawler.process_incidents import process_queued_incidents
    except ImportError:
        from agents.crawler.process_incidents import process_queued_incidents

    max_incidents = _int_env(
        "CRON_MAX_PROCESS_INCIDENTS",
        DEFAULT_MAX_PROCESS_INCIDENTS,
        minimum=0,
    )

    return process_queued_incidents(max_incidents=max_incidents)


def run_safewatch_pipeline() -> dict[str, Any]:
    started_at = datetime.now(timezone.utc)
    started_timer = perf_counter()

    crawler_result = run_crawler_step()
    cleaner_result = run_cleaner_step()
    process_incidents_result = run_process_incidents_step()

    finished_at = datetime.now(timezone.utc)

    return {
        "ok": True,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "duration_seconds": round(perf_counter() - started_timer, 2),
        "steps": {
            "crawler": crawler_result,
            "cleaner": cleaner_result,
            "process_incidents_and_decider": process_incidents_result,
        },
    }
