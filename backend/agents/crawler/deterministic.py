from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT_PATH = PROJECT_ROOT / "data" / "sample_posts.json"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "incident_drafts.json"


CATEGORY_RULES: dict[str, list[str]] = {
    "theft": [
        "stolen",
        "stole",
        "theft",
        "snatched",
        "missing wallet",
        "missing phone",
        "pickpocket",
        "shoplift",
        "took my",
        "taken from",
    ],
    "attempted_theft": [
        "attempted theft",
        "tried to steal",
        "trying to steal",
        "almost stole",
        "tried opening",
        "trying car doors",
        "checking bicycle locks",
    ],
    "vandalism": [
        "vandal",
        "vandalism",
        "spray painted",
        "graffiti",
        "scratched",
        "smashed",
        "damaged",
        "broke the",
    ],
    "suspicious_activity": [
        "suspicious",
        "loitering",
        "following",
        "checking doors",
        "peeking into",
        "filming units",
        "tailgating",
        "prowling",
    ],
    "harassment": [
        "harassed",
        "harassment",
        "threatened",
        "shouted at",
        "followed me",
        "cornered",
        "kept bothering",
        "intimidated",
    ],
}

REJECTION_RULES: dict[str, list[str]] = {
    "joke_or_meme": ["lol", "meme", "joking", "just kidding", "haha", "satire"],
    "general_opinion": [
        "i think crime is",
        "singapore is getting",
        "people nowadays",
        "in my opinion",
        "should have more police",
    ],
    "vague_warning": [
        "be careful everyone",
        "stay safe out there",
        "heard something happened",
        "many incidents lately",
        "avoid this area",
    ],
    "non_crime_complaint": [
        "train delay",
        "noise complaint",
        "dirty toilet",
        "bad service",
        "queue was long",
        "parking expensive",
    ],
    "official_or_mainstream": [
        "reported by police",
        "spf reported",
        "straits times reported",
        "channel newsasia reported",
        "already in the news",
    ],
}

LOCATION_HINTS = [
    "Ang Mo Kio",
    "Bedok",
    "Bishan",
    "Boon Lay",
    "Bugis",
    "Bukit Batok",
    "Bukit Timah",
    "Changi",
    "Chinatown",
    "Choa Chu Kang",
    "Clementi",
    "Dhoby Ghaut",
    "HarbourFront",
    "Hougang",
    "Jurong East",
    "Kallang",
    "Little India",
    "Orchard",
    "Pasir Ris",
    "Punggol",
    "Queenstown",
    "Sengkang",
    "Serangoon",
    "Tampines",
    "Tanjong Pagar",
    "Toa Payoh",
    "Woodlands",
    "Yishun",
]

TIME_PATTERNS = [
    r"\b(?:today|yesterday|tonight|this morning|this afternoon|this evening|last night)\b",
    r"\b(?:around|about|at)\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)\b",
    r"\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b",
    r"\b(?:mon|tue|wed|thu|fri|sat|sun)(?:day)?\b",
]

HANDLE_RE = re.compile(r"@\w+")
PHONE_RE = re.compile(r"\b(?:\+?65\s*)?(?:[689]\d{3}[\s-]?\d{4})\b")
WHITESPACE_RE = re.compile(r"\s+")


def sanitize_text(text: str) -> str:
    text = HANDLE_RE.sub("[redacted-handle]", text)
    text = PHONE_RE.sub("[redacted-phone]", text)
    return WHITESPACE_RE.sub(" ", text).strip()


def normalize_for_duplicate(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9\s]", " ", sanitize_text(text).lower())
    return WHITESPACE_RE.sub(" ", cleaned).strip()


def collect_keyword_hits(text: str, rules: dict[str, list[str]]) -> dict[str, list[str]]:
    lowered = text.lower()
    hits: dict[str, list[str]] = {}

    for label, keywords in rules.items():
        matched = [keyword for keyword in keywords if keyword in lowered]
        if matched:
            hits[label] = matched

    return hits


def score_categories(text: str) -> tuple[dict[str, float], list[str]]:
    hits = collect_keyword_hits(text, CATEGORY_RULES)
    scores = {
        category: round(min(1.0, 0.35 + (0.25 * len(matches))), 2)
        for category, matches in hits.items()
    }
    matched_signals = [
        f"{category}:{keyword}"
        for category, matches in hits.items()
        for keyword in matches
    ]
    return scores, matched_signals


def pick_category(scores: dict[str, float]) -> str | None:
    if not scores:
        return None

    priority = {
        "theft": 5,
        "attempted_theft": 4,
        "harassment": 3,
        "vandalism": 2,
        "suspicious_activity": 1,
    }
    return max(scores, key=lambda category: (scores[category], priority[category]))


def extract_location(text: str) -> str | None:
    lowered = text.lower()
    for location in LOCATION_HINTS:
        if location.lower() in lowered:
            return location
    return None


def extract_time(text: str) -> str | None:
    lowered = text.lower()
    for pattern in TIME_PATTERNS:
        match = re.search(pattern, lowered, flags=re.IGNORECASE)
        if match:
            return match.group(0)
    return None


def evidence_snippets(text: str, matched_signals: list[str]) -> list[str]:
    if not matched_signals:
        return []

    keywords = [signal.split(":", 1)[1] for signal in matched_signals]
    sentences = re.split(r"(?<=[.!?])\s+", sanitize_text(text))
    snippets: list[str] = []

    for sentence in sentences:
        lowered = sentence.lower()
        if any(keyword in lowered for keyword in keywords):
            snippets.append(sentence.strip())

    return snippets[:2]


def rejection_reason(text: str) -> str | None:
    hits = collect_keyword_hits(text, REJECTION_RULES)
    if not hits:
        return None

    reason_priority = [
        "official_or_mainstream",
        "joke_or_meme",
        "non_crime_complaint",
        "vague_warning",
        "general_opinion",
    ]
    for reason in reason_priority:
        if reason in hits:
            return reason

    return next(iter(hits))


def build_incident_id(post: dict[str, Any]) -> str:
    post_id = str(post.get("post_id", "unknown")).strip() or "unknown"
    return f"inc_{post_id}"


def process_post(
    post: dict[str, Any],
    seen_incidents: dict[str, str],
) -> dict[str, Any]:
    raw_text = sanitize_text(str(post.get("text", "")))
    normalized_text = normalize_for_duplicate(raw_text)
    duplicate_of = None

    category_scores, matched_signals = score_categories(raw_text)
    category = pick_category(category_scores)
    reject_reason = rejection_reason(raw_text)
    location_text = extract_location(raw_text)
    timestamp_text = extract_time(raw_text) or str(post.get("timestamp", "")).strip() or None

    status = "candidate"
    candidate = True
    short_reason = "Post contains a specific incident signal."
    notes = ["Crawler used deterministic keyword rules; no LLM call was made."]

    if normalized_text in seen_incidents:
        candidate = False
        status = "rejected_duplicate"
        duplicate_of = seen_incidents[normalized_text]
        short_reason = "Rejected as a duplicate or near-identical mock post."
        notes.append("Duplicate detection matched normalized post text.")
    elif reject_reason:
        candidate = False
        status = "rejected"
        short_reason = f"Rejected by {reject_reason.replace('_', ' ')} rule."
        notes.append(f"Matched rejection rule: {reject_reason}.")
    elif not category:
        candidate = False
        status = "rejected"
        short_reason = "Rejected because no petty-crime or suspicious-activity signal was found."
        notes.append("No category keyword matched the MVP incident categories.")
    elif not (location_text or timestamp_text):
        candidate = False
        status = "needs_context"
        short_reason = "Possible incident, but missing usable location or time context."
        notes.append("Crawler found a category signal but insufficient context.")

    incident_id = build_incident_id(post)
    if normalized_text and normalized_text not in seen_incidents:
        seen_incidents[normalized_text] = incident_id

    return {
        "incident_id": incident_id,
        "post_id": post.get("post_id"),
        "source_platform": post.get("platform", "mock"),
        "source_url": post.get("source_url"),
        "raw_text": raw_text,
        "candidate": candidate,
        "short_reason": short_reason,
        "category": category if candidate else None,
        "severity": None,
        "authenticity_score": None,
        "location_text": location_text,
        "latitude": None,
        "longitude": None,
        "timestamp_text": timestamp_text,
        "normalized_time": post.get("timestamp"),
        "candidate_scores": category_scores,
        "matched_signals": matched_signals,
        "evidence_snippets": evidence_snippets(raw_text, matched_signals) if candidate else [],
        "status": status,
        "duplicate_of": duplicate_of,
        "agent_notes": notes,
    }


def process_posts(posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen_incidents: dict[str, str] = {}

    return [
        process_post(post, seen_incidents)
        for post in posts
    ]


def load_posts(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        posts = json.load(file)

    if not isinstance(posts, list):
        raise ValueError("sample posts file must contain a JSON list")

    return posts


def write_drafts(path: Path, drafts: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(drafts, file, indent=2, ensure_ascii=False)
        file.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the deterministic Crawler Agent.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    posts = load_posts(args.input)
    drafts = process_posts(posts)
    write_drafts(args.output, drafts)

    candidate_count = sum(1 for draft in drafts if draft["candidate"])
    print(f"Created {args.output}")
    print(f"Processed {len(drafts)} posts: {candidate_count} candidates, {len(drafts) - candidate_count} rejected/held")


if __name__ == "__main__":
    main()
