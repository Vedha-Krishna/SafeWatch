export type Severity = "critical" | "high" | "medium" | "low";
export type Trend = "escalating" | "stable" | "declining";

export type AgentDecision = "ACCEPTED" | "REJECTED";

export interface AgentMessage {
  agent: string;
  content: string;
}

export interface AgentLog {
  id: string;
  incident_id?: string | null;
  cleaned_content?: string | null;
  raw_text?: string | null;
  scraped_at: string;
  source: string;
  source_url?: string | null;
  decision: AgentDecision;
  decision_reason?: string | null;
  messages: AgentMessage[];
}

export const DECISION_COLOR: Record<AgentDecision, string> = {
  ACCEPTED: "#22c55e",
  REJECTED: "#ef4444",
};


export interface Incident {
  id: string;
  type: string;
  severity: Severity;
  title: string;
  description: string;
  location: { area: string; lat: number; lng: number };
  hasMapLocation: boolean;
  source: string;
  source_url?: string | null;
  verified: boolean;
  confidence: number;
  timestamp: string;
  cluster_id: string | null;
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

export const mockIncidents: Incident[] = [];
export const mockClusters: Cluster[] = [];

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
