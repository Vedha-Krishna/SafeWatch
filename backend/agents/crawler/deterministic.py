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

LANDMARK_TO_AREA: dict[str, str] = {
    # Orchard / Somerset / Dhoby Ghaut
    "Lucky Plaza": "Orchard",
    "ION Orchard": "Orchard",
    "Plaza Singapura": "Orchard",
    "Wheelock Place": "Orchard",
    "Takashimaya": "Orchard",
    "Ngee Ann City": "Orchard",
    "Paragon": "Orchard",
    "313 Somerset": "Orchard",
    "Orchard Central": "Orchard",
    "The Centrepoint": "Orchard",
    "Wisma Atria": "Orchard",
    "Far East Plaza": "Orchard",
    "Mandarin Gallery": "Orchard",
    "Orchard MRT": "Orchard",
    "Somerset MRT": "Orchard",
    "Dhoby Ghaut MRT": "Orchard",
    "Istana": "Orchard",

    # Bugis / Rochor / Bras Basah
    "Bugis Junction": "Bugis",
    "Bugis+": "Bugis",
    "Bugis Street": "Bugis",
    "Bugis MRT": "Bugis",
    "National Library": "Bugis",
    "Haji Lane": "Bugis",
    "Arab Street": "Bugis",
    "Sultan Mosque": "Bugis",
    "Sim Lim Square": "Bugis",
    "LASALLE College of the Arts": "Bugis",

    # Chinatown / Outram
    "Chinatown Point": "Chinatown",
    "People's Park Complex": "Chinatown",
    "Chinatown MRT": "Chinatown",
    "Maxwell Food Centre": "Chinatown",
    "Buddha Tooth Relic Temple": "Chinatown",
    "Sri Mariamman Temple": "Chinatown",
    "Hong Lim Park": "Chinatown",
    "Outram Park MRT": "Chinatown",

    # Tanjong Pagar / CBD / Marina Bay
    "Suntec City": "Tanjong Pagar",
    "Marina Bay Sands": "Tanjong Pagar",
    "Marina Square": "Tanjong Pagar",
    "Millenia Walk": "Tanjong Pagar",
    "Raffles City": "Tanjong Pagar",
    "Esplanade": "Tanjong Pagar",
    "Merlion Park": "Tanjong Pagar",
    "Gardens by the Bay": "Tanjong Pagar",
    "Marina Bay MRT": "Tanjong Pagar",
    "Bayfront MRT": "Tanjong Pagar",
    "Raffles Place MRT": "Tanjong Pagar",
    "City Hall MRT": "Tanjong Pagar",
    "Tanjong Pagar MRT": "Tanjong Pagar",
    "Lau Pa Sat": "Tanjong Pagar",
    "One Raffles Place": "Tanjong Pagar",
    "Marina One": "Tanjong Pagar",
    "The Shoppes at Marina Bay Sands": "Tanjong Pagar",

    # HarbourFront / Sentosa
    "VivoCity": "HarbourFront",
    "HarbourFront Centre": "HarbourFront",
    "HarbourFront MRT": "HarbourFront",
    "Sentosa": "HarbourFront",
    "Universal Studios Singapore": "HarbourFront",
    "Resorts World Sentosa": "HarbourFront",
    "Siloso Beach": "HarbourFront",
    "Palawan Beach": "HarbourFront",
    "Tanjong Beach": "HarbourFront",
    "S.E.A. Aquarium": "HarbourFront",

    # Jurong East
    "JEM": "Jurong East",
    "Westgate": "Jurong East",
    "IMM": "Jurong East",
    "JCube": "Jurong East",
    "Jurong East MRT": "Jurong East",
    "Ng Teng Fong General Hospital": "Jurong East",
    "Jurong Community Hospital": "Jurong East",
    "Science Centre Singapore": "Jurong East",
    "Chinese Garden": "Jurong East",
    "Japanese Garden": "Jurong East",

    # Jurong West / Boon Lay
    "Jurong Point": "Jurong East",
    "Boon Lay MRT": "Jurong East",
    "Pioneer MRT": "Jurong East",
    "Nanyang Technological University": "Jurong East",
    "NTU": "Jurong East",
    "Jurong West Sports Centre": "Jurong East",

    # Clementi / West Coast
    "The Clementi Mall": "Clementi",
    "Clementi MRT": "Clementi",
    "Clementi Bus Interchange": "Clementi",
    "Singapore Polytechnic": "Clementi",
    "SP": "Clementi",
    "Ngee Ann Polytechnic": "Clementi",
    "NP": "Clementi",
    "SIM": "Clementi",
    "Singapore Institute of Management": "Clementi",
    "West Coast Plaza": "Clementi",
    "West Coast Park": "Clementi",

    # Queenstown / Alexandra / Buona Vista
    "Queenstown MRT": "Queenstown",
    "IKEA Alexandra": "Queenstown",
    "Queensway Shopping Centre": "Queenstown",
    "Alexandra Hospital": "Queenstown",
    "Anchorpoint": "Queenstown",
    "Dawson Place": "Queenstown",
    "The Star Vista": "Queenstown",
    "Buona Vista MRT": "Queenstown",
    "one-north MRT": "Queenstown",
    "Fusionopolis": "Queenstown",
    "Biopolis": "Queenstown",
    "National University of Singapore": "Queenstown",
    "NUS": "Queenstown",
    "NUH": "Queenstown",
    "National University Hospital": "Queenstown",

    # Bukit Timah
    "Beauty World Centre": "Bukit Timah",
    "Beauty World MRT": "Bukit Timah",
    "King Albert Park MRT": "Bukit Timah",
    "Bukit Timah Plaza": "Bukit Timah",
    "Bukit Timah Shopping Centre": "Bukit Timah",
    "Botanic Gardens": "Bukit Timah",
    "Singapore Botanic Gardens": "Bukit Timah",
    "Sixth Avenue": "Bukit Timah",
    "Holland Village": "Bukit Timah",

    # Bukit Batok
    "West Mall": "Bukit Batok",
    "Bukit Batok MRT": "Bukit Batok",
    "Bukit Batok Nature Park": "Bukit Batok",
    "Bukit Batok Swimming Complex": "Bukit Batok",
    "Bukit Gombak MRT": "Bukit Batok",
    "Little Guilin": "Bukit Batok",

    # Choa Chu Kang
    "Lot One": "Choa Chu Kang",
    "Choa Chu Kang MRT": "Choa Chu Kang",
    "Yew Tee Point": "Choa Chu Kang",
    "Yew Tee MRT": "Choa Chu Kang",
    "Keat Hong": "Choa Chu Kang",

    # Woodlands
    "Causeway Point": "Woodlands",
    "Woodlands MRT": "Woodlands",
    "Woodlands Bus Interchange": "Woodlands",
    "Woodlands Civic Centre": "Woodlands",
    "Woodlands Checkpoint": "Woodlands",
    "Republic Polytechnic": "Woodlands",
    "RP": "Woodlands",
    "Admiralty MRT": "Woodlands",
    "Marsiling MRT": "Woodlands",
    "Woodlands North MRT": "Woodlands",
    "Woodlands Waterfront Park": "Woodlands",

    # Sembawang
    "Sun Plaza": "Sembawang",
    "Sembawang MRT": "Sembawang",
    "Canberra Plaza": "Sembawang",
    "Canberra MRT": "Sembawang",
    "Sembawang Shopping Centre": "Sembawang",
    "Sembawang Park": "Sembawang",

    # Yishun
    "Northpoint City": "Yishun",
    "Yishun MRT": "Yishun",
    "Yishun Bus Interchange": "Yishun",
    "Khoo Teck Puat Hospital": "Yishun",
    "KTPH": "Yishun",
    "SAFRA Yishun": "Yishun",
    "Yishun Park": "Yishun",

    # Ang Mo Kio
    "AMK Hub": "Ang Mo Kio",
    "Ang Mo Kio MRT": "Ang Mo Kio",
    "Ang Mo Kio Bus Interchange": "Ang Mo Kio",
    "Bishan-Ang Mo Kio Park": "Ang Mo Kio",
    "Mayflower MRT": "Ang Mo Kio",
    "Lentor MRT": "Ang Mo Kio",

    # Bishan
    "Junction 8": "Bishan",
    "Bishan MRT": "Bishan",
    "Bishan Bus Interchange": "Bishan",
    "Catholic High School": "Bishan",
    "Raffles Institution": "Bishan",
    "RI": "Bishan",

    # Toa Payoh
    "HDB Hub": "Toa Payoh",
    "Toa Payoh MRT": "Toa Payoh",
    "Toa Payoh Bus Interchange": "Toa Payoh",
    "Toa Payoh Central": "Toa Payoh",
    "SAFRA Toa Payoh": "Toa Payoh",
    "Braddell MRT": "Toa Payoh",

    # Novena
    "Velocity": "Novena",
    "Square 2": "Novena",
    "Novena Square": "Novena",
    "Novena MRT": "Novena",
    "Tan Tock Seng Hospital": "Novena",
    "TTSH": "Novena",
    "Mount Elizabeth Novena Hospital": "Novena",
    "United Square": "Novena",

    # Serangoon
    "NEX": "Serangoon",
    "Serangoon MRT": "Serangoon",
    "Serangoon Bus Interchange": "Serangoon",
    "Chomp Chomp Food Centre": "Serangoon",
    "Serangoon Garden": "Serangoon",
    "Lorong Chuan MRT": "Serangoon",

    # Hougang
    "Hougang Mall": "Hougang",
    "Hougang MRT": "Hougang",
    "Hougang Bus Interchange": "Hougang",
    "Heartland Mall": "Hougang",
    "Kovan MRT": "Hougang",
    "Hougang 1": "Hougang",

    # Sengkang
    "Compass One": "Sengkang",
    "Sengkang MRT": "Sengkang",
    "Sengkang Bus Interchange": "Sengkang",
    "Rivervale Mall": "Sengkang",
    "Seletar Mall": "Sengkang",
    "Fernvale LRT": "Sengkang",
    "Sengkang General Hospital": "Sengkang",
    "SKH": "Sengkang",

    # Punggol
    "Waterway Point": "Punggol",
    "Punggol MRT": "Punggol",
    "Punggol Bus Interchange": "Punggol",
    "Punggol Waterway Park": "Punggol",
    "Oasis Terraces": "Punggol",
    "Punggol Plaza": "Punggol",
    "Coney Island": "Punggol",
    "Punggol Digital District": "Punggol",
    "Singapore Institute of Technology": "Punggol",
    "SIT Punggol": "Punggol",

    # Tampines
    "Tampines Mall": "Tampines",
    "Century Square": "Tampines",
    "Tampines 1": "Tampines",
    "Our Tampines Hub": "Tampines",
    "Tampines MRT": "Tampines",
    "Tampines Bus Interchange": "Tampines",
    "Tampines West MRT": "Tampines",
    "Tampines East MRT": "Tampines",
    "IKEA Tampines": "Tampines",
    "Courts Megastore": "Tampines",
    "Giant Tampines": "Tampines",
    "Temasek Polytechnic": "Tampines",
    "TP": "Tampines",

    # Pasir Ris
    "White Sands": "Pasir Ris",
    "Pasir Ris MRT": "Pasir Ris",
    "Pasir Ris Bus Interchange": "Pasir Ris",
    "Pasir Ris Park": "Pasir Ris",
    "Downtown East": "Pasir Ris",
    "E!Hub": "Pasir Ris",
    "Wild Wild Wet": "Pasir Ris",

    # Bedok
    "Bedok Mall": "Bedok",
    "Bedok Point": "Bedok",
    "Bedok MRT": "Bedok",
    "Bedok Bus Interchange": "Bedok",
    "Bedok Reservoir": "Bedok",
    "Bedok Reservoir MRT": "Bedok",
    "Heartbeat@Bedok": "Bedok",
    "East Village": "Bedok",
    "Siglap Centre": "Bedok",

    # Changi
    "Changi Airport": "Changi",
    "Jewel Changi Airport": "Changi",
    "Terminal 1": "Changi",
    "Terminal 2": "Changi",
    "Terminal 3": "Changi",
    "Terminal 4": "Changi",
    "Changi Airport MRT": "Changi",
    "Changi City Point": "Changi",
    "Expo MRT": "Changi",
    "Singapore Expo": "Changi",
    "Changi Business Park": "Changi",
    "Changi Village": "Changi",
    "Changi Beach Park": "Changi",

    # Geylang / Aljunied / Paya Lebar
    "Paya Lebar Square": "Geylang",
    "PLQ Mall": "Geylang",
    "Paya Lebar Quarter": "Geylang",
    "SingPost Centre": "Geylang",
    "Paya Lebar MRT": "Geylang",
    "Aljunied MRT": "Geylang",
    "Geylang Serai Market": "Geylang",
    "Tanjong Katong Complex": "Geylang",
    "City Plaza": "Geylang",

    # Marine Parade / East Coast / Katong
    "Parkway Parade": "Marine Parade",
    "Marine Parade MRT": "Marine Parade",
    "East Coast Park": "Marine Parade",
    "Katong Shopping Centre": "Marine Parade",
    "i12 Katong": "Marine Parade",
    "Katong V": "Marine Parade",
    "Roxy Square": "Marine Parade",
    "Marine Terrace MRT": "Marine Parade",

    # Kallang / Lavender
    "Kallang Wave Mall": "Kallang",
    "Singapore Sports Hub": "Kallang",
    "National Stadium": "Kallang",
    "OCBC Arena": "Kallang",
    "Kallang MRT": "Kallang",
    "Stadium MRT": "Kallang",
    "Lavender MRT": "Kallang",
    "Aperia Mall": "Kallang",
    "Golden Mile Complex": "Kallang",
    "Golden Mile Food Centre": "Kallang",

    # Little India / Farrer Park
    "Mustafa Centre": "Little India",
    "City Square Mall": "Little India",
    "Little India MRT": "Little India",
    "Farrer Park MRT": "Little India",
    "Tekka Centre": "Little India",
    "Sri Veeramakaliamman Temple": "Little India",

    # Balestier / Whampoa
    "Zhongshan Mall": "Balestier",
    "Balestier Plaza": "Balestier",
    "Whampoa Market": "Balestier",
    "Mount Elizabeth Hospital": "Balestier",

    # Bukit Panjang
    "Hillion Mall": "Bukit Panjang",
    "Bukit Panjang Plaza": "Bukit Panjang",
    "Bukit Panjang MRT": "Bukit Panjang",
    "Junction 10": "Bukit Panjang",
    "Senja Cashew Community Club": "Bukit Panjang",

    # Tengah
    "Tengah Plantation MRT": "Tengah",
    "Tengah Park MRT": "Tengah",
    "Tengah Garden": "Tengah",

    # Tuas
    "Tuas Link MRT": "Tuas",
    "Tuas West Road MRT": "Tuas",
    "Tuas Crescent MRT": "Tuas",
    "Tuas Checkpoint": "Tuas",

    # Pioneer / Joo Koon
    "Joo Koon MRT": "Pioneer",
    "FairPrice Hub": "Pioneer",
    "Singapore Discovery Centre": "Pioneer",
    "SAFTI Military Institute": "Pioneer",

    # Yio Chu Kang / Seletar
    "Yio Chu Kang MRT": "Yio Chu Kang",
    "Nanyang Polytechnic": "Yio Chu Kang",
    "NYP": "Yio Chu Kang",
    "Seletar Mall": "Sengkang",
    "Seletar Aerospace Park": "Seletar",
    "The Oval": "Seletar",

    # MacPherson / Ubi / Tai Seng
    "MacPherson MRT": "MacPherson",
    "Tai Seng MRT": "MacPherson",
    "Ubi MRT": "MacPherson",
    "18 Tai Seng": "MacPherson",
    "Paya Ubi Industrial Park": "MacPherson",

    # Potong Pasir
    "Potong Pasir MRT": "Potong Pasir",
    "The Poiz Centre": "Potong Pasir",
    "St Andrew's Village": "Potong Pasir",

    # Bukit Merah / Redhill / Tiong Bahru
    "Tiong Bahru Plaza": "Bukit Merah",
    "Tiong Bahru MRT": "Bukit Merah",
    "Redhill MRT": "Bukit Merah",
    "Bukit Merah Central": "Bukit Merah",
    "Alexandra Retail Centre": "Bukit Merah",
    "ARC": "Bukit Merah",
    "Mount Faber": "Bukit Merah",

    # Commonwealth
    "Commonwealth MRT": "Queenstown",
    "Tanglin Halt": "Queenstown",

    # Tanglin
    "Tanglin Mall": "Tanglin",
    "Dempsey Hill": "Tanglin",
    "Gleneagles Hospital": "Tanglin",
    "Napier MRT": "Tanglin",
    "Orchard Boulevard MRT": "Tanglin",

    # River Valley / Clarke Quay / Robertson Quay
    "Great World": "River Valley",
    "Great World MRT": "River Valley",
    "Clarke Quay": "River Valley",
    "Clarke Quay Central": "River Valley",
    "Robertson Quay": "River Valley",
    "Fort Canning Park": "River Valley",
    "Fort Canning MRT": "River Valley",
    "Liang Court": "River Valley",

    # Bukit Timah / Newton
    "Newton Food Centre": "Newton",
    "Newton MRT": "Newton",
    "United Square": "Novena",

    # Mandai / Zoo
    "Singapore Zoo": "Mandai",
    "Night Safari": "Mandai",
    "River Wonders": "Mandai",
    "Bird Paradise": "Mandai",
    "Mandai Wildlife Reserve": "Mandai",

    # Lim Chu Kang
    "Sungei Buloh Wetland Reserve": "Lim Chu Kang",
    "Kranji Marshes": "Lim Chu Kang",
    "Kranji Countryside": "Lim Chu Kang",
    "Hay Dairies": "Lim Chu Kang",

    # Central Water Catchment
    "MacRitchie Reservoir": "Central Water Catchment",
    "TreeTop Walk": "Central Water Catchment",
    "Upper Seletar Reservoir": "Central Water Catchment",
    "Lower Peirce Reservoir": "Central Water Catchment",

    # Pulau Ubin
    "Pulau Ubin": "Pulau Ubin",
    "Chek Jawa": "Pulau Ubin",

    # Southern Islands
    "St John's Island": "Southern Islands",
    "Kusu Island": "Southern Islands",
    "Lazarus Island": "Southern Islands",
    "Sisters' Islands": "Southern Islands",
}

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
    for landmark, area in LANDMARK_TO_AREA.items():
        if landmark.lower() in lowered:
            return area
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
