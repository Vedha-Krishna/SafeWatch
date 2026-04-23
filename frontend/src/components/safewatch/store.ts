import { create } from "zustand";
import {
  mockIncidents,
  mockClusters,
  type Incident,
  type Cluster,
  type Severity,
} from "./mockData";

// ─────────────────────────────────────────────────────────────────────────────
// The URL of the FastAPI backend.
// If you change the port in main.py, update this too.
// ─────────────────────────────────────────────────────────────────────────────
const API_URL = "http://localhost:8000";

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
export type SeverityFilter = "all" | "critical_only" | "clusters_only";

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

  // Whether the API fetch is currently in progress
  isLoading: boolean;

  toggleSidebar: () => void;
  selectIncident: (id: string | null) => void;
  selectCluster: (id: string | null) => void;
  setCrimeType: (v: CrimeTypeFilter) => void;
  setTimeRange: (v: TimeRangeFilter) => void;
  setSeverityFilter: (v: SeverityFilter) => void;
  flyTo: (lat: number, lng: number, zoom?: number) => void;

  // Fetches published incidents from the FastAPI + Supabase backend.
  // Falls back to mock data if the API is unreachable or returns nothing.
  fetchIncidents: () => Promise<void>;
}

// ─────────────────────────────────────────────────────────────────────────────
// HELPER: Convert a database incident row into the Incident shape
// that the frontend map and sidebar expect.
//
// The database stores severity as a float (0.0 to 1.0).
// The frontend uses a string label: "critical" | "high" | "medium" | "low".
// This function translates between the two formats.
// ─────────────────────────────────────────────────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapDbIncidentToFrontend(row: Record<string, any>): Incident {
  // --- Severity: float → label ---
  const severityFloat = Number(row.severity ?? 0.5);
  const severity: Severity =
    severityFloat >= 0.9 ? "critical" :
    severityFloat >= 0.7 ? "high" :
    severityFloat >= 0.5 ? "medium" : "low";

  // --- Category: use as the incident type ---
  const category = String(row.category ?? "suspicious_activity");

  // --- Human-readable title from category ---
  const titleMap: Record<string, string> = {
    theft:               "Theft",
    attempted_theft:     "Attempted Theft",
    vandalism:           "Vandalism",
    suspicious_activity: "Suspicious Activity",
    harassment:          "Harassment",
  };
  const title = titleMap[category] ?? "Incident";

  // --- Authenticity score becomes confidence ---
  const confidence = Number(row.authenticity_score ?? 0.5);

  return {
    id:          String(row.incident_id),
    type:        category,
    severity,
    title,
    description: String(row.raw_text ?? "No description available."),
    location: {
      area: String(row.location_text ?? "Singapore"),
      lat:  Number(row.latitude  ?? 1.3521),
      lng:  Number(row.longitude ?? 103.8198),
    },
    source:     String(row.source_platform ?? "community"),
    verified:   confidence >= 0.8,
    confidence,
    timestamp:  String(row.normalized_time ?? new Date().toISOString()),
    cluster_id: null,

    // Build a basic agent_analysis summary from the stored scores
    agent_analysis: {
      classification:            title,
      classification_confidence: confidence,
      validation: confidence >= 0.8
        ? "Verified — meets authenticity threshold"
        : "Unverified — below confidence threshold",
      severity_reason:
        severity === "critical" ? "High individual impact, possible repeat pattern" :
        severity === "high"     ? "Significant impact or recurring pattern" :
        severity === "medium"   ? "Moderate impact, isolated incident" :
                                  "Low impact, isolated incident",
      pattern: "Processed by PettyCrimeSG agent pipeline",
    },
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// ZUSTAND STORE
// ─────────────────────────────────────────────────────────────────────────────
export const useStore = create<SafeWatchState>((set) => ({
  // Start with mock data so the map is never blank on first load.
  // fetchIncidents() will replace this with real database data.
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
  selectIncident:   (id)  => set({ selectedIncidentId: id }),
  selectCluster:    (id)  => set({ selectedClusterId: id }),
  setCrimeType:     (v)   => set({ crimeType: v }),
  setTimeRange:     (v)   => set({ timeRange: v }),
  setSeverityFilter:(v)   => set({ severityFilter: v }),
  flyTo: (lat, lng, zoom = 15) =>
    set({ mapFlyTo: { lat, lng, zoom, key: Date.now() } }),

  // ─────────────────────────────────────────────────────────────────────────
  // fetchIncidents
  //
  // Calls the backend API to get all published incidents from Supabase.
  // If the API is down or returns no data, keeps the mock data so the
  // map is never empty during development.
  // ─────────────────────────────────────────────────────────────────────────
  fetchIncidents: async () => {
    set({ isLoading: true });

    try {
      const response = await fetch(
        `${API_URL}/api/db/incidents?published_only=true&limit=200`
      );

      if (!response.ok) {
        throw new Error(`Backend returned status ${response.status}`);
      }

      const data = await response.json();

      // data.incidents is the array of raw database rows
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const dbIncidents = data.incidents as Record<string, any>[];

      if (dbIncidents.length > 0) {
        // We have real data — convert each row and replace mock data
        const mapped = dbIncidents.map(mapDbIncidentToFrontend);
        set({ incidents: mapped, isLoading: false });
        console.log(`Loaded ${mapped.length} incidents from database.`);
      } else {
        // Database is empty — keep mock data so the map still shows something
        console.warn("Database has no published incidents yet. Showing mock data.");
        set({ incidents: mockIncidents, isLoading: false });
      }

    } catch (error) {
      // API is unreachable (backend not started, wrong port, etc.)
      // Fall back to mock data silently so the UI still works
      console.warn("Could not reach backend API. Showing mock data.", error);
      set({ incidents: mockIncidents, isLoading: false });
    }
  },
}));

// ─────────────────────────────────────────────────────────────────────────────
// SELECTOR HOOKS — used by components to read filtered state
// ─────────────────────────────────────────────────────────────────────────────

const TIME_RANGE_HOURS: Record<TimeRangeFilter, number> = {
  "24h": 24,
  "7d":  24 * 7,
  "30d": 24 * 30,
  "90d": 24 * 90,
};

export function useFilteredIncidents(): Incident[] {
  const { incidents, crimeType, timeRange } = useStore();
  const now = Date.now();
  const cutoff = now - TIME_RANGE_HOURS[timeRange] * 3600 * 1000;

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
