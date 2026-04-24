from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT_PATH = PROJECT_ROOT / "data" / "sample_posts.json"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "incident_drafts.json"


CATEGORY_DEFINITIONS = {
    "theft": [
        "Someone stole a wallet, phone, bag, bicycle, parcel, or personal item.",
        "A person took unattended property without permission.",
        "Shoplifting occurred at a store or supermarket.",
        "A victim reported missing belongings believed to be stolen.",
        "Property was taken without force, threats, or unlawful entry.",
        "A delivery parcel was stolen from a doorstep or lobby.",
        "A bicycle or e-scooter was stolen from a rack or public area.",
        "A person dishonestly took another person's belongings but did not use violence.",
    ],

    "burglary": [
        "Someone broke into a home, shop, office, or private premises.",
        "A suspect entered a building unlawfully to steal or commit an offence.",
        "Forced entry was reported at a residential or commercial unit.",
        "A break-in occurred at a house, shop, or office.",
        "Property was stolen after someone entered a premises illegally.",
        "A door, window, lock, or gate was forced open during the incident.",
    ],

    "robbery": [
        "A victim was robbed by someone using force or threats.",
        "Property was taken directly from a person through violence or intimidation.",
        "A mugging occurred in a public place.",
        "A snatch theft involved force or struggle with the victim.",
        "A suspect threatened a victim before taking their belongings.",
        "A victim was attacked and had items stolen.",
    ],

    "assault": [
        "A person was punched, kicked, slapped, shoved, or physically attacked.",
        "A victim was injured or attacked during a dispute.",
        "Someone assaulted a driver, commuter, worker, or member of the public.",
        "A fight resulted in physical harm.",
        "A person was charged for attacking another person.",
        "A victim reported bodily violence without property being stolen.",
        "A person physically attacked another person without theft being involved.",
    ],

    "violent_crime": [
        "A murder, attempted murder, stabbing, or serious violent attack occurred.",
        "A person was killed or seriously injured in a violent crime.",
        "Police investigated a serious assault involving a weapon.",
        "A victim suffered severe harm from a violent attack.",
        "An official report described a serious local violent crime in Singapore.",
        "A serious violent offence involved death, weapons, or severe bodily harm.",
    ],

    "vandalism": [
        "Property was intentionally damaged, defaced, smashed, scratched, or spray-painted.",
        "A wall, vehicle, shopfront, public facility, or building was vandalised.",
        "Someone deliberately damaged public or private property.",
        "Graffiti or deliberate property damage was reported.",
        "Public infrastructure was damaged intentionally.",
    ],

    "scam_fraud": [
        "A scammer impersonated police, bank staff, government officers, or a company.",
        "A victim lost money through deception or fraud.",
        "A phishing, fake website, fake payment, or fake investment scam occurred.",
        "Someone was cheated into transferring money or sharing personal information.",
        "A fraudulent transaction or online scam was reported.",
        "A fake buyer, seller, job offer, investment, or delivery scam was involved.",
        "A person was deceived through impersonation, false claims, or dishonest promises.",
    ],

    "identity_document_fraud": [
        "A person gave a false address, false identity, or false declaration to an authority.",
        "Someone used fake documents, false details, or forged information.",
        "A person lied on an official form or application.",
        "A false address was used for school enrolment, official registration, or eligibility.",
        "The incident involved identity fraud, document fraud, or false official information.",
        "A person was charged or jailed for giving false information to authorities.",
    ],

    "harassment_threat": [
        "A person was threatened, harassed, stalked, intimidated, or verbally abused.",
        "Someone repeatedly disturbed or followed a victim.",
        "A victim received threatening messages or aggressive remarks.",
        "A person behaved aggressively without confirmed physical assault.",
        "A harassment or intimidation incident was reported.",
    ],

    "sexual_offense": [
        "A sexual offence, molestation, voyeurism, or non-consensual sexual conduct occurred.",
        "A person distributed sexual images or sexual content unlawfully.",
        "A victim was sexually harassed, exploited, trafficked, or abused.",
        "An incident involved image-based sexual abuse or voyeurism.",
        "A suspect was charged with a sexual offence.",
    ],

    "suspicious_activity": [
        "A suspicious person was loitering, lurking, peeping, or trying door handles.",
        "Unusual behaviour was reported but no clear crime was confirmed.",
        "A suspicious vehicle or person was seen near homes, shops, or public areas.",
        "The activity suggested possible risk but lacked enough detail for a specific crime.",
        "Someone reported concerning behaviour that may require attention.",
    ],

    "public_disorder": [
        "A public fight, disturbance, nuisance, or disorderly behaviour occurred.",
        "Someone caused a disturbance in a public place.",
        "A person behaved dangerously or disruptively in public.",
        "A public argument or confrontation affected public peace.",
        "A mischief or nuisance incident occurred in a shared public area.",
    ],

    "regulatory_offence": [
        "A person or company was fined for unauthorised works, licensing breaches, or regulatory violations.",
        "A shophouse, building, or business was involved in illegal renovation or administrative enforcement.",
        "The incident involved fines, permits, compliance, or regulatory enforcement.",
        "A company or individual breached government regulations without a direct public safety incident.",
        "This is an administrative offence rather than theft, burglary, robbery, or assault.",
        "A business, building owner, or contractor breached rules or regulations.",
    ],

    "drug_offence": [
        "A person was arrested for drug possession, trafficking, smuggling, or controlled substances.",
        "Police or authorities found illegal drugs or controlled substances.",
        "A suspect was charged with drug-related offences.",
        "A person allegedly imported, sold, possessed, or trafficked drugs.",
        "A controlled substance offence was reported.",
    ],

    "traffic_transport_offence": [
        "A dangerous driving, hit-and-run, road rage, or reckless vehicle incident occurred.",
        "A driver, cyclist, PMD rider, or motorist caused danger in public.",
        "A transport-related offence affected public safety.",
        "A taxi, private-hire, bus, MRT, or road incident involved unsafe behaviour.",
        "A serious road or transport safety incident was reported.",
        "A private-hire driver, taxi driver, passenger, or commuter was involved in a transport safety incident.",
    ],

    "other": [
        "This is general news and not a concrete local Singapore crime or safety incident.",
        "This is business, legal, political, celebrity, corporate, or trend news.",
        "This is a court update or legal commentary without a direct local public safety incident.",
        "This is a corporate feud, business dispute, political issue, or social discussion.",
        "This is weather, lifestyle, economy, property, education, or opinion content.",
        "This is an overseas incident without direct Singapore local public safety impact.",
        "This is too vague, unclear, or irrelevant to classify as a crime incident.",
        "This describes regulatory, administrative, or policy matters unless a concrete crime is involved.",
        "Meal price disputes or customer complaints are not theft unless property was stolen.",
        "Broadband outages, construction mistakes, and infrastructure disruptions are not crime unless intentional damage is reported.",
        "POFMA, political speech, compliance orders, and activism-related charges are not sexual offences or public safety incidents.",
        "Corporate resignations, billionaire disputes, and business leadership changes are not crime incidents.",
        "Heritage business discussions and social commentary are not crime incidents.",
        "Dating app bans or platform restrictions are not crime incidents unless a concrete offence is described.",
        "Defamation trials and legal disputes are not public disorder unless they involve a direct safety incident.",
        "A general trend article about betting, weather, or online behaviour is not a crime incident.",
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

SG_LOCATION_COORDS: dict[str, tuple[float, float]] = {
    "Ang Mo Kio":    (1.3691, 103.8454),
    "Bedok":         (1.3236, 103.9273),
    "Bishan":        (1.3526, 103.8352),
    "Boon Lay":      (1.3404, 103.7090),
    "Bugis":         (1.3009, 103.8555),
    "Bukit Batok":   (1.3490, 103.7495),
    "Bukit Timah":   (1.3294, 103.8021),
    "Changi":        (1.3644, 103.9915),
    "Chinatown":     (1.2836, 103.8444),
    "Choa Chu Kang": (1.3840, 103.7470),
    "Clementi":      (1.3162, 103.7649),
    "Dhoby Ghaut":   (1.2990, 103.8456),
    "HarbourFront":  (1.2650, 103.8198),
    "Hougang":       (1.3613, 103.8863),
    "Jurong East":   (1.3331, 103.7420),
    "Kallang":       (1.3119, 103.8631),
    "Little India":  (1.3066, 103.8518),
    "Orchard":       (1.3048, 103.8318),
    "Pasir Ris":     (1.3730, 103.9494),
    "Punggol":       (1.3984, 103.9072),
    "Queenstown":    (1.2942, 103.8060),
    "Sengkang":      (1.3868, 103.8914),
    "Serangoon":     (1.3554, 103.8679),
    "Tampines":      (1.3530, 103.9450),
    "Tanjong Pagar": (1.2764, 103.8446),
    "Toa Payoh":     (1.3343, 103.8563),
    "Woodlands":     (1.4382, 103.7891),
    "Yishun":        (1.4295, 103.8350),
}


def geocode_location(location_text: str | None) -> tuple[float | None, float | None]:
    if not location_text:
        return None, None
    lowered = location_text.lower()
    for name, (lat, lng) in SG_LOCATION_COORDS.items():
        if name.lower() in lowered:
            return lat, lng
    return None, None

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

    latitude, longitude = geocode_location(location_text)

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
        "latitude": latitude,
        "longitude": longitude,
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
