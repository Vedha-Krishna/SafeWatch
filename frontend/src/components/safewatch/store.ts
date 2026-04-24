import { useEffect, useMemo, useState } from "react";
import { create } from "zustand";
import { supabase } from "../../lib/supabase";
import {
  type Incident,
  type Cluster,
  type Severity,
  type AgentLog,
  type AgentMessage,
} from "./mockData";

// ── Singapore location → coordinates lookup ──────────────────────────────────
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
function normalizeCategory(cat: string | null): string {
  return (cat ?? "uncategorized")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "") || "uncategorized";
}

function mapCategory(cat: string | null): string {
  const normalized = normalizeCategory(cat);

  switch (normalized) {
    case "theft":
    case "attempted_theft": return "theft";
    case "vandalism":       return "vandalism";
    case "robbery":         return "snatch_theft";
    case "scam_fraud":      return "scam";
    case "harassment_threat":
    case "assault":
    case "sexual_offense":
    case "harassment":      return "harassment";
    default:                return normalized;
  }
}

// ── Numeric severity → enum ───────────────────────────────────────────────────
function mapSeverity(score: number | null): Severity {
  if (score === null) return "medium";
  if (score >= 0.7)  return "critical";
  if (score >= 0.5)  return "high";
  if (score >= 0.3)  return "medium";
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
  timestamp_text:     string | null;
  normalized_time:    string | null;
  created_at:         string | null;
  decision?:          string | null;
  agent_messages?:    string | null;
}

function validIsoTimestamp(value: string | null | undefined): string | null {
  if (!value) return null;
  const trimmed = value.trim();
  if (!trimmed) return null;
  return Number.isNaN(new Date(trimmed).getTime()) ? null : trimmed;
}

function rowToIncident(r: DbRow): Incident {
  // Use DB coordinates if available, fall back to lookup, then SG center
  const [fallbackLat, fallbackLng] = geocode(r.location_text);
  const lat = r.latitude ?? fallbackLat;
  const lng = r.longitude ?? fallbackLng;
  const confidence = r.authenticity_score ?? 0.5;
  const description = r.cleaned_content || r.raw_text || "";
  const categoryLabel = r.category
    ? r.category.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
    : "Incident";
  const postCreatedAt =
    validIsoTimestamp(r.timestamp_text) ?? validIsoTimestamp(r.normalized_time);

  return {
    id: r.incident_id,
    type: mapCategory(r.category),
    severity: mapSeverity(r.severity),
    title: categoryLabel,
    description,
    location: { area: r.location_text ?? "Singapore", lat, lng },
    source: r.source_platform ?? "unknown",
    verified: r.cleaned_content !== null,
    confidence,
    timestamp: postCreatedAt ?? "",
    cluster_id: null,
  };
}

function mapDecisionToAgentDecision(decision?: string | null): AgentLog["decision"] {
  if (!decision) return "REJECTED";
  const normalized = decision.toLowerCase();
  if (normalized === "publish" || normalized === "accepted") return "ACCEPTED";
  return "REJECTED";
}

function extractAgentContent(m: Record<string, unknown>): string {
  const lines: string[] = [];

  // Primary label (note or reasoning)
  const primary = typeof m.note === "string" ? m.note
    : typeof m.reasoning === "string" ? m.reasoning
    : typeof m.content === "string" ? m.content
    : null;
  if (primary) lines.push(primary);

  // Incident summary used for vector embedding
  if (typeof m.incident_summary_used === "string" && m.incident_summary_used)
    lines.push(`used: "${m.incident_summary_used}"`);

  // Top-3 candidate scores
  if (m.candidate_scores && typeof m.candidate_scores === "object") {
    const scores = m.candidate_scores as Record<string, number>;
    const top3 = Object.entries(scores)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 3)
      .map(([k, v]) => `${k.replace(/_/g, " ")} ${(v * 100).toFixed(1)}%`)
      .join(" · ");
    lines.push(`scores: ${top3}`);
  }

  // Rubric features — split into ✓ / ✗ groups
  if (m.features && typeof m.features === "object") {
    const features = m.features as Record<string, boolean>;
    const yes = Object.entries(features).filter(([, v]) => v).map(([k]) => k.replace(/_/g, " "));
    const no  = Object.entries(features).filter(([, v]) => !v).map(([k]) => k.replace(/_/g, " "));
    if (yes.length) lines.push(`✓ ${yes.join(", ")}`);
    if (no.length)  lines.push(`✗ ${no.join(", ")}`);
  }

  // Extracted location / time / action
  if (m.extracted_fields && typeof m.extracted_fields === "object") {
    const f = m.extracted_fields as Record<string, unknown>;
    const parts = (["location", "time", "action"] as const)
      .filter((k) => f[k] != null && String(f[k]) !== "null")
      .map((k) => `${k}: ${f[k]}`);
    if (parts.length) lines.push(parts.join(" · "));
  }

  // Decision feedback fields
  if (typeof m.instruction === "string" && m.instruction) lines.push(m.instruction);
  if (typeof m.reason      === "string" && m.reason)      lines.push(m.reason);

  // Last-resort raw output
  if (lines.length === 0 && typeof m.raw_output === "string" && m.raw_output)
    lines.push(m.raw_output);

  return lines.join("\n");
}

function rowToAgentLog(r: DbRow): AgentLog {
  let raw: Record<string, unknown>[] = [];

  if (r.agent_messages) {
    try {
      // agent_messages may arrive as a string (text column) or already-parsed
      // array (jsonb column) depending on Supabase column type.
      const parsed = typeof r.agent_messages === "string"
        ? JSON.parse(r.agent_messages)
        : r.agent_messages;
      if (Array.isArray(parsed)) raw = parsed as Record<string, unknown>[];
    } catch {
      raw = [];
    }
  }

  // Extract decision_reason from raw data before normalising messages.
  const rawDecision = raw.find(
    (m) => m.agent === "decision" && typeof m.decision_reason === "string",
  );
  const decision_reason = rawDecision
    ? (rawDecision.decision_reason as string)
    : null;

  const messages: AgentMessage[] = raw.map((m) => ({
    agent: typeof m.agent === "string" ? m.agent
         : typeof m.role  === "string" ? m.role
         : "unknown",
    content: extractAgentContent(m),
  }));

  return {
    id: r.incident_id,
    incident_id: r.incident_id,
    raw_text: r.raw_text,
    scraped_at: r.created_at ?? new Date().toISOString(),
    source: r.source_platform ?? "unknown",
    decision: mapDecisionToAgentDecision(r.decision),
    decision_reason,
    messages,
  };
}

// ── Zustand store ─────────────────────────────────────────────────────────────
export type CrimeTypeFilter = "all" | (string & {});

export type TimeRangeFilter = "24h" | "7d" | "30d" | "90d";
export type SeverityFilter = "all" | "critical_only" | "no_location";

interface SafeWatchState {
  incidents: Incident[];
  clusters: Cluster[];
  selectedIncidentId: string | null;
  agentLogsOpen: boolean;
  setAgentLogsOpen: (open: boolean) => void;
  agentLogs: AgentLog[];
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
  loadIncidents: () => Promise<void>;
  loadAgentLogs: () => Promise<void>;
}

export const useStore = create<SafeWatchState>((set) => ({
  incidents: [],
  clusters: [],
  selectedIncidentId: null,
  selectedClusterId: null,
  crimeType: "all",
  timeRange: "7d",
  severityFilter: "all",
  mapFlyTo: null,
  sidebarCollapsed:
    typeof window !== "undefined" && window.innerWidth < 640,
  agentLogsOpen: false,
  agentLogs: [],
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  setAgentLogsOpen: (open) => set({ agentLogsOpen: open }),
  selectIncident: (id) => set({ selectedIncidentId: id }),
  selectCluster: (id) => set({ selectedClusterId: id }),
  setCrimeType: (v) => set({ crimeType: v }),
  setTimeRange: (v) => set({ timeRange: v }),
  setSeverityFilter: (v) => set({ severityFilter: v }),
  flyTo: (lat, lng, zoom = 15) =>
    set({ mapFlyTo: { lat, lng, zoom, key: Date.now() } }),
  loadIncidents: async () => {
    const { data, error } = await supabase
      .from("incidents")
      .select("incident_id, source_platform, raw_text, cleaned_content, status, category, authenticity_score, severity, location_text, latitude, longitude, timestamp_text, normalized_time, created_at")
      .order("created_at", { ascending: false })
      .limit(200);

    if (error) {
      console.error("Failed to load incidents from Supabase:", error.message);
      return;
    }

    console.log("Supabase raw response:", data);
    const incidents = (data as DbRow[]).map(rowToIncident);
    console.log("Mapped incidents:", incidents.length);
    set({ incidents });
  },
  loadAgentLogs: async () => {
    const { data, error } = await supabase
      .from("incidents")
      .select("incident_id, source_platform, raw_text, decision, agent_messages, created_at")
      .not("agent_messages", "is", null)
      .order("created_at", { ascending: false })
      .limit(200);

    if (error) {
      console.error("Failed to load agent logs from Supabase:", error.message);
      return;
    }

    console.log("Supabase agent logs response:", data);
    const agentLogs = (data as DbRow[]).map(rowToAgentLog);
    console.log("Mapped agent logs:", agentLogs.length);
    set({ agentLogs });
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
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 60_000);
    return () => window.clearInterval(id);
  }, []);

  return useMemo(() => {
    const cutoff = now - TIME_RANGE_HOURS[timeRange] * 3600 * 1000;
    return incidents.filter((i) => {
      if (crimeType !== "all" && i.type !== crimeType) return false;
      const postedAt = new Date(i.timestamp).getTime();
      if (Number.isNaN(postedAt)) return true;
      return postedAt >= cutoff;
    });
  }, [crimeType, incidents, now, timeRange]);
}

export function severityCounts(incidents: Incident[]): Record<Severity, number> {
  const out: Record<Severity, number> = { critical: 0, high: 0, medium: 0, low: 0 };
  for (const i of incidents) out[i.severity]++;
  return out;
}

export function timeAgo(iso: string): string {
  const time = new Date(iso).getTime();
  if (Number.isNaN(time)) return "Unknown time";
  const diffMs = Date.now() - time;
  const mins = Math.round(diffMs / 60000);
  if (mins < 60) return `${mins} min ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs} hr${hrs === 1 ? "" : "s"} ago`;
  const days = Math.round(hrs / 24);
  return `${days} day${days === 1 ? "" : "s"} ago`;
}

export function formatTimestamp(iso: string): string {
  const time = new Date(iso);
  if (Number.isNaN(time.getTime())) return "Unknown time";
  return time.toLocaleString("en-SG", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}
