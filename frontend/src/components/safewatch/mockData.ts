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

export const mockIncidents: Incident[] = [];

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
