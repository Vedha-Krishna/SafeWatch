import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  X,
  MapPin,
  Clock,
  Radio,
  ExternalLink,
} from "lucide-react";
import { useStore, formatTimestamp, timeAgo } from "./store";
import { SEVERITY_COLOR, SEVERITY_LABEL, SG_CENTER, SG_ZOOM } from "./mockData";

export default function IncidentDetailPanel() {
  const { selectedIncidentId, incidents, selectIncident, flyTo } = useStore();
  const incident = incidents.find((i) => i.id === selectedIncidentId);
  const sourceUrl = incident ? normalizeSourceUrl(incident.source_url) : null;

  const handleClose = () => {
    selectIncident(null);
    flyTo(SG_CENTER[0], SG_CENTER[1], SG_ZOOM);
  };

  return (
    <AnimatePresence mode="wait">
      {incident && (
        <motion.div
          key={incident.id}
          initial={{ y: "100%", opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: "100%", opacity: 0 }}
          transition={{ type: "spring", damping: 28, stiffness: 220 }}
          className="absolute bottom-0 left-0 right-0 z-[1100] max-h-[70%] sm:max-h-[45%] overflow-y-auto safewatch-scroll bg-[#0d1117]/85 backdrop-blur-xl border-t border-white/10 shadow-2xl"
        >
          <button
            onClick={handleClose}
            className="absolute top-3 right-3 p-1.5 rounded-md text-slate-400 hover:text-white hover:bg-white/5 transition-colors z-10"
          >
            <X className="w-4 h-4" />
          </button>

          <div className="p-3 sm:p-5 space-y-3 sm:space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2 sm:gap-4 pr-10">
              <div className="flex items-center gap-2 sm:gap-3 min-w-0">
                <span
                  className="w-3 h-3 rounded-full shrink-0"
                  style={{
                    backgroundColor: SEVERITY_COLOR[incident.severity],
                    boxShadow: `0 0 12px ${SEVERITY_COLOR[incident.severity]}`,
                  }}
                />
                <h2 className="text-base sm:text-xl font-bold text-white font-mono uppercase tracking-wide truncate">
                  {incident.title}
                </h2>
              </div>
              <span
                className="self-start text-[10px] sm:text-[11px] font-mono uppercase font-bold px-2 py-1 rounded border whitespace-nowrap"
                style={{
                  color: SEVERITY_COLOR[incident.severity],
                  borderColor: `${SEVERITY_COLOR[incident.severity]}66`,
                  backgroundColor: `${SEVERITY_COLOR[incident.severity]}15`,
                }}
              >
                Severity: {SEVERITY_LABEL[incident.severity]}
              </span>
            </div>

            <div className="flex flex-wrap gap-x-5 gap-y-1.5 text-xs text-slate-400 font-mono">
              <span className="flex items-center gap-1.5">
                <MapPin className="w-3.5 h-3.5 text-slate-500" />
                {incident.location.area}
              </span>
              <span className="flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-slate-500" />
                Posted {timeAgo(incident.timestamp)} - {formatTimestamp(incident.timestamp)}
              </span>
              <span className="flex items-center gap-1.5">
                <Radio className="w-3.5 h-3.5 text-slate-500" />
                {sourceUrl ? (
                  <a
                    href={sourceUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-blue-300 hover:text-blue-200 transition-colors underline decoration-blue-400/40 underline-offset-2"
                    title={`Open source post on ${incident.source}`}
                  >
                    Source: {incident.source}
                    <ExternalLink className="w-3 h-3" />
                  </a>
                ) : (
                  <span>Source: {incident.source}</span>
                )}
              </span>
            </div>

            <Section title="Description">
              <p className="text-sm text-slate-200 italic">
                "{incident.description}"
              </p>
            </Section>


            <RelatedIncidents
              currentId={incident.id}
              clusterId={incident.cluster_id}
              onSelect={(id, lat, lng) => {
                selectIncident(id);
                flyTo(lat, lng, 16);
              }}
            />
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function normalizeSourceUrl(value?: string | null): string | null {
  if (!value) return null;
  const trimmed = value.trim();
  if (!trimmed) return null;
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  if (/^www\./i.test(trimmed)) return `https://${trimmed}`;
  return null;
}

function Section({
  title,
  icon,
  children,
}: {
  title: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-[11px] font-mono uppercase tracking-wider text-slate-500 border-b border-white/5 pb-1">
        {icon}
        {title}
      </div>
      <div>{children}</div>
    </div>
  );
}


function RelatedIncidents({
  currentId,
  clusterId,
  onSelect,
}: {
  currentId: string;
  clusterId: string | null;
  onSelect: (id: string, lat: number, lng: number) => void;
}) {
  const { incidents } = useStore();
  if (!clusterId) return null;
  const related = incidents.filter(
    (i) => i.cluster_id === clusterId && i.id !== currentId,
  );
  if (related.length === 0) return null;

  return (
    <Section title="Related Incidents (same cluster)">
      <ul className="space-y-1">
        {related.map((r) => (
          <li key={r.id}>
            <button
              onClick={() => onSelect(r.id, r.location.lat, r.location.lng)}
              className="text-xs text-slate-300 hover:text-blue-400 font-mono w-full text-left flex items-center gap-2 hover:bg-white/5 px-2 py-1 rounded"
            >
              <span
                className="w-1.5 h-1.5 rounded-full"
                style={{ backgroundColor: SEVERITY_COLOR[r.severity] }}
              />
              <span className="flex-1">
                {r.title} — {r.location.area}
              </span>
              <span className="text-slate-500">{timeAgo(r.timestamp)}</span>
            </button>
          </li>
        ))}
      </ul>
    </Section>
  );
}
