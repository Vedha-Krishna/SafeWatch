import { create } from "zustand";
import { supabase } from "../../lib/supabase";
import {
  mockIncidents,
  mockClusters,
  type Incident,
  type Cluster,
  type Severity,
} from "./mockData";

// ── Singapore location → coordinates lookup ───────────────────────────────────
const SG_COORDS: Record<string, [number, number]> = {
  "ang mo kio":    [1.3691, 103.8454],
  "bedok":         [1.3236, 103.9273],
  "bishan":        [1.3526, 103.8352],
  "boon lay":      [1.3404, 103.7090],
  "bugis":         [1.3009, 103.8555],
  "bukit batok":   [1.3490, 103.7495],
  "bukit timah":   [1.3294, 103.8021],
  "changi":        [1.3644, 103.9915],
  "chinatown":     [1.2836, 103.8444],
  "choa chu kang": [1.3840, 103.7470],
  "clementi":      [1.3162, 103.7649],
  "dhoby ghaut":   [1.2990, 103.8456],
  "harbourfront":  [1.2650, 103.8198],
  "hougang":       [1.3613, 103.8863],
  "jurong east":   [1.3331, 103.7420],
  "kallang":       [1.3119, 103.8631],
  "little india":  [1.3066, 103.8518],
  "orchard":       [1.3048, 103.8318],
  "pasir ris":     [1.3730, 103.9494],
  "punggol":       [1.3984, 103.9072],
  "queenstown":    [1.2942, 103.8060],
  "sengkang":      [1.3868, 103.8914],
  "serangoon":     [1.3554, 103.8679],
  "tampines":      [1.3530, 103.9450],
  "tanjong pagar": [1.2764, 103.8446],
  "toa payoh":     [1.3343, 103.8563],
  "woodlands":     [1.4382, 103.7891],
  "yishun":        [1.4295, 103.8350],
};

function geocode(locationText: string | null): [number, number] {
  if (!locationText) return [1.3521, 103.8198];
  const lower = locationText.toLowerCase();
  for (const [name, coords] of Object.entries(SG_COORDS)) {
    if (lower.includes(name)) return coords;
  }
  return [1.3521, 103.8198];
}

// ── Category mapping ──────────────────────────────────────────────────────────
function mapCategory(cat: string | null): string {
  switch (cat) {
    case "theft":
    case "attempted_theft":   return "theft";
    case "vandalism":         return "vandalism";
    case "robbery":           return "snatch_theft";
    case "scam_fraud":        return "scam";
    case "harassment_threat":
    case "assault":
    case "sexual_offense":
    case "harassment":        return "harassment";
    default:                  return "theft";
  }
}

// ── Numeric severity → enum ───────────────────────────────────────────────────
function mapSeverity(score: number | null): Severity {
  if (score === null) return "medium";
  if (score >= 0.7)   return "critical";
  if (score >= 0.5)   return "high";
  if (score >= 0.3)   return "medium";
  return "low";
}

// ── DB row → Incident ─────────────────────────────────────────────────────────
interface DbRow {
  incident_id:        string;
  source_platform:    string | null;
  raw_text:           string | null;
  cleaned_content:    string | null;
  status:             string | null;
  category:           string | null;
  authenticity_score: number | null;
  severity:           number | null;
  location_text:      string | null;
  latitude:           number | null;
  longitude:          number | null;
  normalized_time:    string | null;
  created_at:         string | null;
}

function rowToIncident(r: DbRow): Incident {
  const [fallbackLat, fallbackLng] = geocode(r.location_text);
  const lat = r.latitude ?? fallbackLat;
  const lng = r.longitude ?? fallbackLng;
  const confidence = r.authenticity_score ?? 0.5;
  const description = r.cleaned_content || r.raw_text || "";
  const categoryLabel = r.category
    ? r.category.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
    : "Incident";

  return {
    id:       r.incident_id,
    type:     mapCategory(r.category),
    severity: mapSeverity(r.severity),
    title:    categoryLabel,
    description,
    location: { area: r.location_text ?? "Singapore", lat, lng },
    source:   r.source_platform ?? "unknown",
    verified: r.cleaned_content !== null,
    confidence,
    timestamp:  r.normalized_time ?? r.created_at ?? new Date().toISOString(),
    cluster_id: null,
    agent_analysis: {
      classification:            r.category ?? "Unknown",
      classification_confidence: confidence,
      validation:                r.status ?? "unknown",
      severity_reason:           "Processed by cleaner agent",
      pattern:                   "Isolated incident — no cluster detected",
    },
  };
}

// ── Zustand store ─────────────────────────────────────────────────────────────
export type CrimeTypeFilter =
  | "all"
  | "snatch_theft"
  | "bike_theft"
  | "scam"
  | "vandalism"
  | "harassment"
  | "theft"
  | "loan_shark";

export type TimeRangeFilter = "24h" | "7d" | "30d" | "90d";
export type SeverityFilter = "all" | "critical_only" | "no_location";

interface SafeWatchState {
  incidents: Incident[];
  clusters: Cluster[];
  selectedIncidentId: string | null;
  selectedClusterId: string | null;
  crimeType: CrimeTypeFilter;
  timeRange: TimeRangeFilter;
  severityFilter: SeverityFilter;
  mapFlyTo: { lat: number; lng: number; zoom: number; key: number } | null;
  sidebarCollapsed: boolean;
  isLoading: boolean;

  toggleSidebar: () => void;
  selectIncident: (id: string | null) => void;
  selectCluster: (id: string | null) => void;
  setCrimeType: (v: CrimeTypeFilter) => void;
  setTimeRange: (v: TimeRangeFilter) => void;
  setSeverityFilter: (v: SeverityFilter) => void;
  flyTo: (lat: number, lng: number, zoom?: number) => void;
  loadIncidents: () => Promise<void>;
}

export const useStore = create<SafeWatchState>((set) => ({
  // Start with mock data so the map is never blank on first load.
  // loadIncidents() will replace this with real Supabase data.
  incidents: mockIncidents,
  clusters:  mockClusters,

  selectedIncidentId: null,
  selectedClusterId:  null,
  crimeType:          "all",
  timeRange:          "7d",
  severityFilter:     "all",
  mapFlyTo:           null,
  isLoading:          false,

  sidebarCollapsed:
    typeof window !== "undefined" && window.innerWidth < 640,

  toggleSidebar:    () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  selectIncident:   (id) => set({ selectedIncidentId: id }),
  selectCluster:    (id) => set({ selectedClusterId: id }),
  setCrimeType:     (v)  => set({ crimeType: v }),
  setTimeRange:     (v)  => set({ timeRange: v }),
  setSeverityFilter:(v)  => set({ severityFilter: v }),
  flyTo: (lat, lng, zoom = 15) =>
    set({ mapFlyTo: { lat, lng, zoom, key: Date.now() } }),

  loadIncidents: async () => {
    set({ isLoading: true });

    const { data, error } = await supabase
      .from("incidents")
      .select(
        "incident_id, source_platform, raw_text, cleaned_content, status, " +
        "category, authenticity_score, severity, location_text, latitude, " +
        "longitude, normalized_time, created_at"
      )
      .order("created_at", { ascending: false })
      .limit(200);

    if (error) {
      console.error("Failed to load incidents from Supabase:", error.message);
      set({ incidents: mockIncidents, isLoading: false });
      return;
    }

    const incidents = (data as DbRow[]).map(rowToIncident);

    if (incidents.length > 0) {
      console.log(`Loaded ${incidents.length} incidents from Supabase.`);
      set({ incidents, isLoading: false });
    } else {
      console.warn("No incidents in Supabase yet. Showing mock data.");
      set({ incidents: mockIncidents, isLoading: false });
    }
  },
}));

// ── Derived selectors ─────────────────────────────────────────────────────────
const TIME_RANGE_HOURS: Record<TimeRangeFilter, number> = {
  "24h": 24,
  "7d":  24 * 7,
  "30d": 24 * 30,
  "90d": 24 * 90,
};

export function useFilteredIncidents(): Incident[] {
  const { incidents, crimeType, timeRange } = useStore();
  const cutoff = Date.now() - TIME_RANGE_HOURS[timeRange] * 3600 * 1000;

  return incidents.filter((i) => {
    if (crimeType !== "all" && i.type !== crimeType) return false;
    return new Date(i.timestamp).getTime() >= cutoff;
  });
}

export function severityCounts(incidents: Incident[]): Record<Severity, number> {
  const out: Record<Severity, number> = { critical: 0, high: 0, medium: 0, low: 0 };
  for (const i of incidents) out[i.severity]++;
  return out;
}

export function timeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.round(diffMs / 60000);
  if (mins < 60) return `${mins} min ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs} hr${hrs === 1 ? "" : "s"} ago`;
  const days = Math.round(hrs / 24);
  return `${days} day${days === 1 ? "" : "s"} ago`;
}
