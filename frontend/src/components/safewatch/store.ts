import { create } from "zustand";
import {
  mockIncidents,
  mockClusters,
  type Incident,
  type Cluster,
  type Severity,
} from "./mockData";

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
  toggleSidebar: () => void;
  selectIncident: (id: string | null) => void;
  selectCluster: (id: string | null) => void;
  setCrimeType: (v: CrimeTypeFilter) => void;
  setTimeRange: (v: TimeRangeFilter) => void;
  setSeverityFilter: (v: SeverityFilter) => void;
  flyTo: (lat: number, lng: number, zoom?: number) => void;
}

export const useStore = create<SafeWatchState>((set) => ({
  incidents: mockIncidents,
  clusters: mockClusters,
  selectedIncidentId: null,
  selectedClusterId: null,
  crimeType: "all",
  timeRange: "7d",
  severityFilter: "all",
  mapFlyTo: null,
  sidebarCollapsed:
    typeof window !== "undefined" && window.innerWidth < 640,
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  selectIncident: (id) => set({ selectedIncidentId: id }),
  selectCluster: (id) => set({ selectedClusterId: id }),
  setCrimeType: (v) => set({ crimeType: v }),
  setTimeRange: (v) => set({ timeRange: v }),
  setSeverityFilter: (v) => set({ severityFilter: v }),
  flyTo: (lat, lng, zoom = 15) =>
    set({ mapFlyTo: { lat, lng, zoom, key: Date.now() } }),
}));

const TIME_RANGE_HOURS: Record<TimeRangeFilter, number> = {
  "24h": 24,
  "7d": 24 * 7,
  "30d": 24 * 30,
  "90d": 24 * 90,
};

export function useFilteredIncidents(): Incident[] {
  const { incidents, crimeType, timeRange } = useStore();
  const now = new Date("2026-04-18T16:00:00+08:00").getTime();
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
  const now = new Date("2026-04-18T16:00:00+08:00").getTime();
  const diffMs = now - new Date(iso).getTime();
  const mins = Math.round(diffMs / 60000);
  if (mins < 60) return `${mins} min ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs} hr${hrs === 1 ? "" : "s"} ago`;
  const days = Math.round(hrs / 24);
  return `${days} day${days === 1 ? "" : "s"} ago`;
}
