export type Severity = "critical" | "high" | "medium" | "low";
export type Trend = "escalating" | "stable" | "declining";

export interface AgentAnalysis {
  classification: string;
  classification_confidence: number;
  validation: string;
  severity_reason: string;
  pattern: string;
}

export interface Incident {
  id: string;
  type: string;
  severity: Severity;
  title: string;
  description: string;
  location: { area: string; lat: number; lng: number };
  source: string;
  verified: boolean;
  confidence: number;
  timestamp: string;
  cluster_id: string | null;
  agent_analysis: AgentAnalysis;
}

export interface Cluster {
  id: string;
  type: string;
  area: string;
  center: { lat: number; lng: number };
  radius_km: number;
  incident_count: number;
  days_span: number;
  trend: Trend;
  severity: Severity;
  incidents: string[];
}

export const SG_CENTER: [number, number] = [1.3521, 103.8198];
export const SG_ZOOM = 12;

export const mockIncidents: Incident[] = [
  {
    id: "INC_001",
    type: "snatch_theft",
    severity: "critical",
    title: "Snatch Theft",
    description:
      "Woman had phone snatched while walking. Suspect fled on e-scooter towards Sims Avenue.",
    location: { area: "Geylang Lorong 25", lat: 1.3163, lng: 103.893 },
    source: "Reddit r/singapore",
    verified: true,
    confidence: 0.94,
    timestamp: "2026-04-18T14:34:00+08:00",
    cluster_id: "CL_023",
    agent_analysis: {
      classification: "Snatch Theft",
      classification_confidence: 0.94,
      validation: "Corroborated by 2 sources",
      severity_reason: "Matches pattern of 3 similar incidents this week",
      pattern: "Part of cluster CL_023 — 5 incidents in Geylang, last 10 days",
    },
  },
  {
    id: "INC_002",
    type: "bike_theft",
    severity: "high",
    title: "Bicycle Theft",
    description:
      "Locked bicycle stolen from rack at Tampines MRT Exit B. Cut lock found on ground.",
    location: { area: "Tampines MRT", lat: 1.3545, lng: 103.9453 },
    source: "HardwareZone Forum",
    verified: true,
    confidence: 0.87,
    timestamp: "2026-04-18T11:20:00+08:00",
    cluster_id: "CL_019",
    agent_analysis: {
      classification: "Bike Theft",
      classification_confidence: 0.87,
      validation: "Verified — matches 3 other reports at same location",
      severity_reason: "3.3x above baseline for this location",
      pattern: "Part of cluster CL_019 — 4 incidents at Tampines MRT, last 14 days",
    },
  },
  {
    id: "INC_003",
    type: "scam",
    severity: "high",
    title: "Carousell Scam",
    description:
      "Seller asked to move to WhatsApp, sent fake PayNow screenshot. Multiple victims reporting same account.",
    location: { area: "Online — multiple victims in Woodlands", lat: 1.4382, lng: 103.7891 },
    source: "Reddit r/singapore",
    verified: true,
    confidence: 0.91,
    timestamp: "2026-04-18T09:45:00+08:00",
    cluster_id: null,
    agent_analysis: {
      classification: "Online Scam",
      classification_confidence: 0.91,
      validation: "Verified — 4 victims identified same seller account",
      severity_reason: "Active scam with multiple victims, ongoing",
      pattern: "No geographic cluster — online scam",
    },
  },
  {
    id: "INC_004",
    type: "vandalism",
    severity: "medium",
    title: "Vandalism",
    description:
      "Multiple cars in carpark scratched overnight. At least 5 vehicles affected.",
    location: { area: "Bukit Batok St 21, Block 208", lat: 1.3483, lng: 103.7496 },
    source: "Telegram — BB Residents Group",
    verified: false,
    confidence: 0.62,
    timestamp: "2026-04-18T07:15:00+08:00",
    cluster_id: null,
    agent_analysis: {
      classification: "Vandalism",
      classification_confidence: 0.78,
      validation: "Unverified — single source only",
      severity_reason: "Multiple vehicles affected but no repeat pattern",
      pattern: "Isolated incident — no cluster detected",
    },
  },
  {
    id: "INC_005",
    type: "harassment",
    severity: "critical",
    title: "Voyeurism",
    description:
      "Resident reported peeping tom at Block 743. Third report this month at the same block.",
    location: { area: "Yishun Block 743", lat: 1.4295, lng: 103.835 },
    source: "OneService App",
    verified: true,
    confidence: 0.89,
    timestamp: "2026-04-17T23:10:00+08:00",
    cluster_id: "CL_031",
    agent_analysis: {
      classification: "Voyeurism / Sexual Harassment",
      classification_confidence: 0.89,
      validation: "Verified — third report at same block this month",
      severity_reason: "Repeat offender pattern, same location",
      pattern: "Part of cluster CL_031 — 3 incidents at Yishun Blk 743, last 30 days",
    },
  },
  {
    id: "INC_006",
    type: "theft",
    severity: "medium",
    title: "Package Theft",
    description: "Parcel stolen from outside door. Delivery confirmed but package missing.",
    location: { area: "Punggol Block 312", lat: 1.3984, lng: 103.9072 },
    source: "Reddit r/singapore",
    verified: false,
    confidence: 0.55,
    timestamp: "2026-04-17T18:30:00+08:00",
    cluster_id: null,
    agent_analysis: {
      classification: "Package Theft",
      classification_confidence: 0.71,
      validation: "Unverified — could be delivery error",
      severity_reason: "Low individual impact, no repeat pattern",
      pattern: "Isolated incident",
    },
  },
  {
    id: "INC_007",
    type: "loan_shark",
    severity: "high",
    title: "Loan Shark Harassment",
    description:
      "Red paint and threatening note splashed on door of unit. Neighbours report this is the second time.",
    location: { area: "Bedok North Block 512", lat: 1.3276, lng: 103.947 },
    source: "Straits Times",
    verified: true,
    confidence: 0.96,
    timestamp: "2026-04-17T14:20:00+08:00",
    cluster_id: null,
    agent_analysis: {
      classification: "Loan Shark Harassment",
      classification_confidence: 0.96,
      validation: "Verified — news report with police confirmation",
      severity_reason: "Repeat targeting, property damage, intimidation",
      pattern: "Second incident at same unit — possible targeted harassment",
    },
  },
  {
    id: "INC_008",
    type: "snatch_theft",
    severity: "high",
    title: "Snatch Theft",
    description:
      "Elderly man had gold chain snatched near market. Suspect ran towards Lor 27.",
    location: { area: "Geylang Lorong 27", lat: 1.3155, lng: 103.8945 },
    source: "CNA",
    verified: true,
    confidence: 0.92,
    timestamp: "2026-04-16T16:45:00+08:00",
    cluster_id: "CL_023",
    agent_analysis: {
      classification: "Snatch Theft",
      classification_confidence: 0.92,
      validation: "Verified — news report",
      severity_reason: "Part of escalating cluster in Geylang",
      pattern: "Part of cluster CL_023 — 5 incidents in Geylang, last 10 days",
    },
  },

  // ─── GEYLANG cluster (10+ heat) ─────────────────────────────
  ai("INC_009", "snatch_theft", "high",     "Snatch Theft",     "Tourist had bag snatched outside hotel near Sims Ave.",       "Geylang Sims Avenue",       1.3171, 103.8918, "Reddit r/singapore", true,  0.88, "2026-04-15T22:10:00+08:00", "CL_023"),
  ai("INC_010", "snatch_theft", "critical", "Snatch Theft",     "Phone snatched from young woman near Geylang Lor 9.",         "Geylang Lorong 9",          1.3140, 103.8870, "Mothership",         true,  0.93, "2026-04-14T19:30:00+08:00", "CL_023"),
  ai("INC_011", "harassment",   "high",     "Public Harassment","Group of men reported harassing pedestrians at Lor 17.",       "Geylang Lorong 17",         1.3158, 103.8902, "Telegram — SG Watch", false, 0.71, "2026-04-13T23:50:00+08:00", null),
  ai("INC_012", "theft",        "medium",   "Pickpocketing",    "Wallet stolen on bus near Geylang interchange.",               "Geylang Bahru",             1.3210, 103.8720, "Reddit r/singapore", true,  0.79, "2026-04-12T08:20:00+08:00", null),
  ai("INC_013", "vandalism",    "medium",   "Graffiti",         "Walls of HDB block tagged overnight near Aljunied MRT.",       "Geylang — Aljunied Road",   1.3180, 103.8840, "OneService App",     false, 0.65, "2026-04-10T05:00:00+08:00", null),
  ai("INC_014", "snatch_theft", "critical", "Snatch Theft",     "Senior citizen pushed and robbed of handbag near coffeeshop.", "Geylang Lorong 21",         1.3168, 103.8920, "Straits Times",      true,  0.95, "2026-04-08T18:15:00+08:00", "CL_023"),
  ai("INC_015", "scam",         "medium",   "Door-to-door scam","Fake utility worker tried to enter HDB unit.",                 "Geylang East",              1.3185, 103.8965, "Telegram — SG Watch", false, 0.60, "2026-04-05T14:00:00+08:00", null),
  ai("INC_016", "loan_shark",   "high",     "Loan Shark Splash","Door splashed with paint, threatening note left at HDB unit.", "Geylang Lorong 31",         1.3149, 103.8961, "Straits Times",      true,  0.94, "2026-04-02T03:30:00+08:00", null),
  ai("INC_017", "theft",        "low",      "Bicycle Theft",    "Folding bike stolen from void deck.",                          "Geylang Lor 38",            1.3138, 103.8980, "HardwareZone",       false, 0.55, "2026-03-28T16:00:00+08:00", null),
  ai("INC_018", "snatch_theft", "high",     "Attempted Snatch", "Man attempted to grab bag, fled when victim screamed.",        "Geylang Road",              1.3152, 103.8895, "Reddit r/singapore", true,  0.86, "2026-03-22T21:45:00+08:00", "CL_023"),

  // ─── YISHUN (7-9 heat) ──────────────────────────────────────
  ai("INC_019", "harassment",   "high",     "Voyeurism Report", "Resident saw man filming through bathroom window.",            "Yishun Block 745",          1.4288, 103.8345, "OneService App",     true,  0.86, "2026-04-15T01:30:00+08:00", "CL_031"),
  ai("INC_020", "harassment",   "critical", "Voyeurism Report", "Third report of peeping tom this month at same block.",        "Yishun Block 743",          1.4295, 103.8350, "Reddit r/singapore", true,  0.91, "2026-04-12T22:15:00+08:00", "CL_031"),
  ai("INC_021", "theft",        "medium",   "Package Theft",    "Multiple parcels stolen from corridor.",                       "Yishun Avenue 6",           1.4310, 103.8395, "Reddit r/singapore", false, 0.58, "2026-04-09T11:00:00+08:00", null),
  ai("INC_022", "vandalism",    "low",      "Lift Vandalism",   "Lift buttons damaged repeatedly.",                              "Yishun Street 11",          1.4271, 103.8360, "OneService App",     false, 0.52, "2026-04-04T03:00:00+08:00", null),
  ai("INC_023", "scam",         "medium",   "Carousell Scam",   "Fake seller account targeting Yishun residents.",              "Yishun (online seller)",    1.4298, 103.8355, "Reddit r/singapore", true,  0.82, "2026-03-30T15:30:00+08:00", null),
  ai("INC_024", "snatch_theft", "high",     "Snatch Theft",     "Phone snatched at Yishun MRT exit.",                           "Yishun MRT",                1.4293, 103.8353, "CNA",                true,  0.90, "2026-03-25T19:00:00+08:00", null),
  ai("INC_025", "harassment",   "high",     "Stalking Report",  "Female resident reported being followed home twice.",          "Yishun Ring Road",          1.4280, 103.8330, "Telegram — SG Watch", true,  0.84, "2026-03-20T22:00:00+08:00", "CL_031"),

  // ─── TAMPINES (4-6 heat) ────────────────────────────────────
  ai("INC_026", "bike_theft",   "high",     "Bicycle Theft",    "Two bikes cut and stolen overnight.",                          "Tampines Block 201",        1.3540, 103.9445, "HardwareZone",       true,  0.83, "2026-04-15T07:00:00+08:00", "CL_019"),
  ai("INC_027", "bike_theft",   "medium",   "Bicycle Theft",    "Bike stolen from void deck — lock cut.",                       "Tampines Avenue 4",         1.3520, 103.9430, "Reddit r/singapore", true,  0.80, "2026-04-11T14:00:00+08:00", "CL_019"),
  ai("INC_028", "theft",        "medium",   "Shop Theft",       "Suspect stole goods from minimart and ran.",                   "Tampines Mall area",        1.3526, 103.9447, "Mothership",         true,  0.78, "2026-04-06T16:30:00+08:00", null),
  ai("INC_029", "bike_theft",   "low",      "Bicycle Theft",    "PMD stolen from corridor.",                                    "Tampines Street 21",        1.3533, 103.9420, "OneService App",     false, 0.50, "2026-03-26T09:00:00+08:00", "CL_019"),

  // ─── BEDOK (2-3 heat) ───────────────────────────────────────
  ai("INC_030", "loan_shark",   "high",     "Loan Shark Visit", "Door splashed second time at same unit.",                      "Bedok North Block 510",     1.3275, 103.9460, "Straits Times",      true,  0.92, "2026-04-13T02:00:00+08:00", null),
  ai("INC_031", "vandalism",    "medium",   "Car Scratching",   "Multiple cars in carpark damaged overnight.",                  "Bedok South",               1.3215, 103.9270, "Telegram — SG Watch", false, 0.62, "2026-03-29T05:00:00+08:00", null),

  // ─── BUKIT BATOK (2-3 heat) ─────────────────────────────────
  ai("INC_032", "vandalism",    "medium",   "Lift Damage",      "Lift mirrors smashed in two HDB blocks.",                      "Bukit Batok Block 210",     1.3492, 103.7510, "OneService App",     false, 0.59, "2026-04-09T04:00:00+08:00", null),

  // ─── PUNGGOL (2 heat) ───────────────────────────────────────
  ai("INC_033", "theft",        "low",      "Package Theft",    "Two parcels stolen from same corridor on different days.",     "Punggol Block 315",         1.3990, 103.9080, "Reddit r/singapore", false, 0.54, "2026-04-07T18:00:00+08:00", null),

  // ─── Singles spread across more areas (cyan heat) ──────────
  ai("INC_034", "scam",         "high",     "Investment Scam",  "Resident lost SGD 12k to fake crypto investment platform.",     "Jurong West",               1.3404, 103.7090, "Straits Times",      true,  0.93, "2026-04-14T11:00:00+08:00", null),
  ai("INC_035", "bike_theft",   "medium",   "Bicycle Theft",    "E-bike stolen from MRT station racks.",                         "Ang Mo Kio MRT",            1.3691, 103.8454, "Reddit r/singapore", true,  0.77, "2026-04-13T08:30:00+08:00", null),
  ai("INC_036", "harassment",   "medium",   "Verbal Harassment","Group of teens verbally harassed elderly residents.",           "Toa Payoh Lor 1",           1.3343, 103.8563, "Telegram — SG Watch", false, 0.66, "2026-04-12T20:00:00+08:00", null),
  ai("INC_037", "snatch_theft", "high",     "Snatch Theft",     "Handphone snatched outside Hougang Mall.",                     "Hougang",                   1.3613, 103.8863, "CNA",                true,  0.89, "2026-04-10T17:30:00+08:00", null),
  ai("INC_038", "scam",         "medium",   "Phishing SMS",     "Multiple residents reported PayNow phishing texts.",            "Sengkang",                  1.3868, 103.8914, "Reddit r/singapore", true,  0.81, "2026-04-08T13:00:00+08:00", null),
  ai("INC_039", "theft",        "low",      "Cafe Laptop Theft","Laptop stolen from cafe table when victim left briefly.",      "Clementi",                  1.3162, 103.7649, "HardwareZone",       false, 0.57, "2026-04-06T15:45:00+08:00", null),
  ai("INC_040", "vandalism",    "low",      "Spray Paint",      "Graffiti on void deck pillars.",                                "Bukit Merah",               1.2819, 103.8237, "OneService App",     false, 0.51, "2026-04-04T06:00:00+08:00", null),
  ai("INC_041", "bike_theft",   "low",      "Bicycle Theft",    "Bike taken from carpark — no lock used.",                       "Queenstown",                1.2942, 103.8060, "Reddit r/singapore", false, 0.48, "2026-04-02T19:00:00+08:00", null),
  ai("INC_042", "scam",         "high",     "Job Scam",         "Fake recruiter scam targeting Kallang residents.",              "Kallang",                   1.3119, 103.8631, "Mothership",         true,  0.85, "2026-03-31T10:30:00+08:00", null),
  ai("INC_043", "theft",        "medium",   "Wallet Theft",     "Wallet stolen on MRT during peak hour.",                        "Bishan MRT",                1.3526, 103.8352, "Reddit r/singapore", true,  0.74, "2026-03-27T08:15:00+08:00", null),
  ai("INC_044", "harassment",   "medium",   "Public Harassment","Drunk man harassed customers at hawker centre.",                "Serangoon",                 1.3554, 103.8679, "Telegram — SG Watch", false, 0.60, "2026-03-23T22:00:00+08:00", null),
  ai("INC_045", "vandalism",    "low",      "Property Damage",  "Car windows smashed in carpark — wallet stolen.",               "Choa Chu Kang",             1.3840, 103.7470, "OneService App",     true,  0.70, "2026-03-21T03:00:00+08:00", null),

  // ─── Older than 30 days (only visible with 90d filter) ──────
  ai("INC_046", "snatch_theft", "high",     "Snatch Theft",     "Snatch theft outside hawker centre.",                           "Geylang Lorong 23",         1.3162, 103.8915, "CNA",                true,  0.88, "2026-03-15T20:00:00+08:00", null),
  ai("INC_047", "scam",         "high",     "Romance Scam",     "Resident lost SGD 30k to overseas romance scam.",               "Novena",                    1.3203, 103.8434, "Straits Times",      true,  0.92, "2026-03-10T14:00:00+08:00", null),
  ai("INC_048", "theft",        "medium",   "Shoplifting",      "Group of suspects shoplifted from convenience store.",          "Rochor",                    1.3030, 103.8520, "Mothership",         true,  0.75, "2026-03-05T16:30:00+08:00", null),
  ai("INC_049", "loan_shark",   "high",     "Loan Shark Splash","Red paint splashed on door of HDB unit.",                       "Outram",                    1.2789, 103.8398, "Straits Times",      true,  0.91, "2026-02-28T03:30:00+08:00", null),
  ai("INC_050", "harassment",   "critical", "Voyeurism Arrest", "Suspect arrested after series of voyeurism reports.",           "Yishun",                    1.4290, 103.8345, "CNA",                true,  0.96, "2026-02-22T10:00:00+08:00", "CL_031"),
  ai("INC_051", "vandalism",    "medium",   "Bus Stop Vandalism","Bus stop glass shattered, repeat offender suspected.",          "Tampines Avenue 7",         1.3530, 103.9450, "OneService App",     false, 0.63, "2026-02-15T05:00:00+08:00", null),
  ai("INC_052", "snatch_theft", "high",     "Snatch Theft",     "Old case — phone snatched near Geylang market.",                "Geylang Lorong 11",         1.3145, 103.8880, "Reddit r/singapore", true,  0.85, "2026-02-08T19:30:00+08:00", null),
  ai("INC_053", "scam",         "medium",   "WhatsApp Scam",    "Hijacked WhatsApp account scammed contacts.",                   "Woodlands",                 1.4382, 103.7891, "Reddit r/singapore", true,  0.79, "2026-02-01T12:00:00+08:00", null),
  ai("INC_054", "bike_theft",   "low",      "Bicycle Theft",    "Bike stolen from carpark — last month.",                        "Tampines Block 480",        1.3510, 103.9460, "HardwareZone",       false, 0.50, "2026-01-25T14:00:00+08:00", null),
  ai("INC_055", "theft",        "low",      "Package Theft",    "Old report — package taken from doorstep.",                     "Hougang Avenue 3",          1.3620, 103.8870, "Reddit r/singapore", false, 0.47, "2026-01-18T11:00:00+08:00", null),
];

// Compact factory so the data block above stays readable.
// Auto-generates a generic 5-field agent_analysis from the basics.
function ai(
  id: string,
  type: string,
  severity: Severity,
  title: string,
  description: string,
  area: string,
  lat: number,
  lng: number,
  source: string,
  verified: boolean,
  confidence: number,
  timestamp: string,
  cluster_id: string | null,
): Incident {
  return {
    id, type, severity, title, description,
    location: { area, lat, lng },
    source, verified, confidence, timestamp, cluster_id,
    agent_analysis: {
      classification: title,
      classification_confidence: confidence,
      validation: verified
        ? "Verified — corroborated by source"
        : "Unverified — single source",
      severity_reason:
        severity === "critical" ? "High individual impact, repeat pattern likely"
      : severity === "high"     ? "Significant impact or part of recurring pattern"
      : severity === "medium"   ? "Moderate impact, isolated incident"
      :                           "Low impact, isolated incident",
      pattern: cluster_id
        ? `Part of cluster ${cluster_id}`
        : "Isolated incident — no cluster detected",
    },
  };
}

export const mockClusters: Cluster[] = [
  {
    id: "CL_023",
    type: "Snatch Theft",
    area: "Geylang",
    center: { lat: 1.316, lng: 103.8935 },
    radius_km: 0.8,
    incident_count: 5,
    days_span: 10,
    trend: "escalating",
    severity: "critical",
    incidents: ["INC_001", "INC_008"],
  },
  {
    id: "CL_019",
    type: "Bike Theft",
    area: "Tampines MRT",
    center: { lat: 1.3545, lng: 103.9453 },
    radius_km: 0.3,
    incident_count: 4,
    days_span: 14,
    trend: "stable",
    severity: "high",
    incidents: ["INC_002"],
  },
  {
    id: "CL_031",
    type: "Voyeurism",
    area: "Yishun Block 743",
    center: { lat: 1.4295, lng: 103.835 },
    radius_km: 0.1,
    incident_count: 3,
    days_span: 30,
    trend: "stable",
    severity: "critical",
    incidents: ["INC_005"],
  },
];

export const SEVERITY_COLOR: Record<Severity, string> = {
  critical: "#ef4444",
  high: "#f97316",
  medium: "#eab308",
  low: "#22c55e",
};

export const SEVERITY_LABEL: Record<Severity, string> = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
};
